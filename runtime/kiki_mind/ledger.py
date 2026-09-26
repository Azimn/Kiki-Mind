from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, sqlite3, uuid
from pathlib import Path
from typing import Iterator
from .gate import GateDecision, TransitionGate
from .models import (
    ActorKind, AncestryEdge, ClaimDomain, DerivationMode, EpistemicClass,
    EventProposal, EventRecord, EventType, Restriction,
)

class IntegrityError(RuntimeError):
    pass

class IdempotencyConflict(RuntimeError):
    pass

class GateRejected(ValueError):
    def __init__(self, decision: GateDecision):
        self.decision = decision
        super().__init__("; ".join(decision.details) or "transition rejected")

def _canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _proposal_hash(proposal: EventProposal) -> str:
    material = {
        "event_type": proposal.event_type.value,
        "actor_kind": proposal.actor_kind.value,
        "actor_id": proposal.actor_id,
        "epistemic_class": proposal.epistemic_class.value,
        "claim_domain": proposal.claim_domain.value,
        "payload": dict(proposal.payload),
        "ancestry": [{"event_id":e.event_id,"mode":e.mode.value} for e in proposal.ancestry],
        "causal_parent_ids": list(proposal.causal_parent_ids),
        "content_restrictions": sorted(r.value for r in proposal.content_restrictions),
        "renderer_mediated": proposal.renderer_mediated,
        "renderer_id": proposal.renderer_id,
        "policy_version": proposal.policy_version,
        "idempotency_key": proposal.idempotency_key,
    }
    return hashlib.sha256(_canonical_json(material).encode()).hexdigest()

class _TxView:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_event(self, event_id: str) -> EventRecord | None:
        row = self.conn.execute("SELECT * FROM canonical_events WHERE event_id=?", (event_id,)).fetchone()
        return _row_to_record(row) if row else None

    def renderer_exists(self, renderer_id: str) -> bool:
        row = self.conn.execute(
            """SELECT 1 FROM canonical_events
               WHERE event_type=? AND json_extract(payload_json,'$.renderer_id')=?
               LIMIT 1""",
            (EventType.RENDERER_REGISTERED.value, renderer_id),
        ).fetchone()
        return row is not None

    def has_any_operator_lease(self) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM canonical_events WHERE event_type IN (?,?) LIMIT 1",
            (EventType.OPERATOR_LEASE_GRANTED.value, EventType.OPERATOR_LEASE_RENEWED.value),
        ).fetchone() is not None

    def active_operator_lease(self, operator_id: str, at: datetime) -> tuple[bool, str]:
        row = self.conn.execute(
            """SELECT payload_json FROM canonical_events
               WHERE event_type IN (?,?)
                 AND json_extract(payload_json,'$.operator_id')=?
               ORDER BY sequence DESC LIMIT 1""",
            (EventType.OPERATOR_LEASE_GRANTED.value, EventType.OPERATOR_LEASE_RENEWED.value, operator_id),
        ).fetchone()
        if row is None:
            return False, "missing"
        payload = json.loads(row["payload_json"])
        try:
            expiry = datetime.fromisoformat(str(payload["expires_at"]).replace("Z","+00:00"))
        except Exception:
            return False, "missing"
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        return (True, "ok") if at < expiry else (False, "expired")

    def endorsement_proposal_exists(self, proposal_event_id: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM canonical_events WHERE event_id=? AND event_type=?",
            (proposal_event_id, EventType.CANONICAL_ENDORSEMENT_PROPOSED.value),
        ).fetchone() is not None

class EventLedger:
    """Append-only SQLite canonical event ledger."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    def _initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS canonical_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                committed_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_kind TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                epistemic_class TEXT NOT NULL,
                claim_domain TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                ancestry_json TEXT NOT NULL,
                causal_parent_ids_json TEXT NOT NULL,
                content_restrictions_json TEXT NOT NULL,
                renderer_mediated INTEGER NOT NULL CHECK(renderer_mediated IN (0,1)),
                renderer_id TEXT,
                policy_version TEXT NOT NULL,
                idempotency_key TEXT UNIQUE,
                proposal_hash TEXT NOT NULL,
                prev_event_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE
            );
            CREATE TRIGGER IF NOT EXISTS canonical_events_no_update
            BEFORE UPDATE ON canonical_events
            BEGIN SELECT RAISE(ABORT,'canonical event ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS canonical_events_no_delete
            BEFORE DELETE ON canonical_events
            BEGIN SELECT RAISE(ABORT,'canonical event ledger is append-only'); END;
            CREATE INDEX IF NOT EXISTS idx_event_type ON canonical_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_actor ON canonical_events(actor_kind,actor_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def get_event(self, event_id: str) -> EventRecord | None:
        conn = self._connect()
        try:
            return _TxView(conn).get_event(event_id)
        finally:
            conn.close()

    def iter_events(self) -> Iterator[EventRecord]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM canonical_events ORDER BY sequence").fetchall()
        finally:
            conn.close()
        for row in rows:
            yield _row_to_record(row)

    def commit(self, proposal: EventProposal, gate: TransitionGate, *, event_id: str | None=None) -> EventRecord:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            view = _TxView(conn)
            proposal_hash = _proposal_hash(proposal)
            if proposal.idempotency_key:
                row = conn.execute(
                    "SELECT * FROM canonical_events WHERE idempotency_key=?",
                    (proposal.idempotency_key,),
                ).fetchone()
                if row:
                    if row["proposal_hash"] != proposal_hash:
                        conn.rollback()
                        raise IdempotencyConflict(
                            "idempotency key reused for a different event proposal"
                        )
                    conn.rollback()
                    return _row_to_record(row)

            decision = gate.validate(proposal, view)
            if not decision.accepted:
                conn.rollback()
                raise GateRejected(decision)

            eid = event_id or str(uuid.uuid4())
            committed_at = datetime.now(timezone.utc).isoformat()
            prev = conn.execute(
                "SELECT event_hash FROM canonical_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            prev_hash = prev["event_hash"] if prev else "GENESIS"
            material = {
                "event_id": eid,
                "committed_at": committed_at,
                "event_type": proposal.event_type.value,
                "actor_kind": proposal.actor_kind.value,
                "actor_id": proposal.actor_id,
                "epistemic_class": proposal.epistemic_class.value,
                "claim_domain": proposal.claim_domain.value,
                "payload": dict(proposal.payload),
                "ancestry": [{"event_id":e.event_id,"mode":e.mode.value} for e in proposal.ancestry],
                "causal_parent_ids": list(proposal.causal_parent_ids),
                "content_restrictions": sorted(r.value for r in proposal.content_restrictions),
                "renderer_mediated": proposal.renderer_mediated,
                "renderer_id": proposal.renderer_id,
                "policy_version": proposal.policy_version,
                "idempotency_key": proposal.idempotency_key,
                "proposal_hash": proposal_hash,
                "prev_event_hash": prev_hash,
            }
            event_hash = hashlib.sha256(_canonical_json(material).encode()).hexdigest()
            cur = conn.execute(
                """INSERT INTO canonical_events(
                    event_id,committed_at,event_type,actor_kind,actor_id,
                    epistemic_class,claim_domain,payload_json,ancestry_json,
                    causal_parent_ids_json,content_restrictions_json,
                    renderer_mediated,renderer_id,policy_version,idempotency_key,
                    proposal_hash,prev_event_hash,event_hash
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    eid, committed_at, proposal.event_type.value, proposal.actor_kind.value,
                    proposal.actor_id, proposal.epistemic_class.value, proposal.claim_domain.value,
                    _canonical_json(dict(proposal.payload)),
                    _canonical_json([{"event_id":e.event_id,"mode":e.mode.value} for e in proposal.ancestry]),
                    _canonical_json(list(proposal.causal_parent_ids)),
                    _canonical_json(sorted(r.value for r in proposal.content_restrictions)),
                    1 if proposal.renderer_mediated else 0, proposal.renderer_id,
                    proposal.policy_version, proposal.idempotency_key, proposal_hash, prev_hash, event_hash,
                ),
            )
            seq = cur.lastrowid
            conn.commit()
            row = conn.execute("SELECT * FROM canonical_events WHERE sequence=?", (seq,)).fetchone()
            return _row_to_record(row)
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def verify_integrity(self):
        prev_hash = "GENESIS"
        for r in self.iter_events():
            material = {
                "event_id":r.event_id,"committed_at":r.committed_at,
                "event_type":r.event_type.value,"actor_kind":r.actor_kind.value,
                "actor_id":r.actor_id,"epistemic_class":r.epistemic_class.value,
                "claim_domain":r.claim_domain.value,"payload":dict(r.payload),
                "ancestry":[{"event_id":e.event_id,"mode":e.mode.value} for e in r.ancestry],
                "causal_parent_ids":list(r.causal_parent_ids),
                "content_restrictions":sorted(x.value for x in r.content_restrictions),
                "renderer_mediated":r.renderer_mediated,"renderer_id":r.renderer_id,
                "policy_version":r.policy_version,"idempotency_key":r.idempotency_key,
                "proposal_hash":_proposal_hash(EventProposal(
                    event_type=r.event_type, actor_kind=r.actor_kind, actor_id=r.actor_id,
                    epistemic_class=r.epistemic_class, claim_domain=r.claim_domain,
                    payload=r.payload, ancestry=r.ancestry, causal_parent_ids=r.causal_parent_ids,
                    content_restrictions=r.content_restrictions,
                    renderer_mediated=r.renderer_mediated, renderer_id=r.renderer_id,
                    policy_version=r.policy_version, idempotency_key=r.idempotency_key,
                )),
                "prev_event_hash":r.prev_event_hash,
            }
            if r.prev_event_hash != prev_hash:
                raise IntegrityError(f"predecessor hash mismatch at sequence {r.sequence}")
            expected = hashlib.sha256(_canonical_json(material).encode()).hexdigest()
            if r.event_hash != expected:
                raise IntegrityError(f"event hash mismatch at sequence {r.sequence}")
            prev_hash = r.event_hash

def _row_to_record(row: sqlite3.Row) -> EventRecord:
    return EventRecord(
        event_id=row["event_id"], sequence=row["sequence"], committed_at=row["committed_at"],
        event_type=EventType(row["event_type"]), actor_kind=ActorKind(row["actor_kind"]),
        actor_id=row["actor_id"], epistemic_class=EpistemicClass(row["epistemic_class"]),
        claim_domain=ClaimDomain(row["claim_domain"]), payload=json.loads(row["payload_json"]),
        ancestry=tuple(AncestryEdge(x["event_id"],DerivationMode(x["mode"]))
                       for x in json.loads(row["ancestry_json"])),
        causal_parent_ids=tuple(json.loads(row["causal_parent_ids_json"])),
        content_restrictions=frozenset(Restriction(x) for x in json.loads(row["content_restrictions_json"])),
        renderer_mediated=bool(row["renderer_mediated"]), renderer_id=row["renderer_id"],
        policy_version=row["policy_version"], idempotency_key=row["idempotency_key"],
        prev_event_hash=row["prev_event_hash"], event_hash=row["event_hash"],
    )
