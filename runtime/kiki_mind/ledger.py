"""Canonical history for Kiki Mind.

This is the boring wall in the best possible sense. Events may accumulate,
renderers may change, projections may catch fire in parachute pants, but
canonical history remains append-only, attributable, and inspectable.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Iterator

from .gate import GateDecision, TransitionGate
from .models import (
    ActorKind,
    AncestryEdge,
    ClaimDomain,
    DerivationMode,
    EpistemicClass,
    EventProposal,
    EventRecord,
    EventType,
    Restriction,
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
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _proposal_hash(proposal: EventProposal) -> str:
    material = {
        "event_type": proposal.event_type.value,
        "actor_kind": proposal.actor_kind.value,
        "actor_id": proposal.actor_id,
        "epistemic_class": proposal.epistemic_class.value,
        "claim_domain": proposal.claim_domain.value,
        "payload": dict(proposal.payload),
        "ancestry": [
            {"event_id": e.event_id, "mode": e.mode.value}
            for e in proposal.ancestry
        ],
        "causal_parent_ids": list(proposal.causal_parent_ids),
        "content_restrictions": sorted(
            r.value for r in proposal.content_restrictions
        ),
        "renderer_mediated": proposal.renderer_mediated,
        "renderer_id": proposal.renderer_id,
        "policy_version": proposal.policy_version,
        "idempotency_key": proposal.idempotency_key,
    }
    return hashlib.sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()


def _proposal_from_record(record: EventRecord) -> EventProposal:
    return EventProposal(
        event_type=record.event_type,
        actor_kind=record.actor_kind,
        actor_id=record.actor_id,
        epistemic_class=record.epistemic_class,
        claim_domain=record.claim_domain,
        payload=record.payload,
        ancestry=record.ancestry,
        causal_parent_ids=record.causal_parent_ids,
        content_restrictions=record.content_restrictions,
        renderer_mediated=record.renderer_mediated,
        renderer_id=record.renderer_id,
        policy_version=record.policy_version,
        idempotency_key=record.idempotency_key,
    )


def _event_material(record: EventRecord) -> dict:
    return {
        "event_id": record.event_id,
        "committed_at": record.committed_at,
        "event_type": record.event_type.value,
        "actor_kind": record.actor_kind.value,
        "actor_id": record.actor_id,
        "epistemic_class": record.epistemic_class.value,
        "claim_domain": record.claim_domain.value,
        "payload": dict(record.payload),
        "ancestry": [
            {"event_id": e.event_id, "mode": e.mode.value}
            for e in record.ancestry
        ],
        "causal_parent_ids": list(record.causal_parent_ids),
        "content_restrictions": sorted(
            x.value for x in record.content_restrictions
        ),
        "renderer_mediated": record.renderer_mediated,
        "renderer_id": record.renderer_id,
        "policy_version": record.policy_version,
        "idempotency_key": record.idempotency_key,
        "proposal_hash": _proposal_hash(_proposal_from_record(record)),
        "prev_event_hash": record.prev_event_hash,
    }


class _TxView:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_event(self, event_id: str) -> EventRecord | None:
        row = self.conn.execute(
            "SELECT * FROM canonical_events WHERE event_id=?",
            (event_id,),
        ).fetchone()
        return _row_to_record(row) if row else None

    def renderer_exists(self, renderer_id: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1
            FROM canonical_events
            WHERE event_type=?
              AND json_extract(payload_json,'$.renderer_id')=?
            LIMIT 1
            """,
            (EventType.RENDERER_REGISTERED.value, renderer_id),
        ).fetchone()
        return row is not None

    def has_any_operator_lease(self) -> bool:
        return self.conn.execute(
            """
            SELECT 1
            FROM canonical_events
            WHERE event_type IN (?,?)
            LIMIT 1
            """,
            (
                EventType.OPERATOR_LEASE_GRANTED.value,
                EventType.OPERATOR_LEASE_RENEWED.value,
            ),
        ).fetchone() is not None

    def operator_lease_status(
        self,
        operator_id: str,
        at: datetime,
    ) -> tuple[str, EventRecord | None]:
        row = self.conn.execute(
            """
            SELECT *
            FROM canonical_events
            WHERE event_type IN (?,?)
              AND json_extract(payload_json,'$.operator_id')=?
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (
                EventType.OPERATOR_LEASE_GRANTED.value,
                EventType.OPERATOR_LEASE_RENEWED.value,
                operator_id,
            ),
        ).fetchone()

        if row is None:
            return "missing", None

        record = _row_to_record(row)
        try:
            expiry = datetime.fromisoformat(
                str(record.payload["expires_at"]).replace("Z", "+00:00")
            )
        except Exception:
            return "missing", record

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)

        expiry = expiry.astimezone(timezone.utc)
        at = at.astimezone(timezone.utc)
        return ("active", record) if at < expiry else ("expired", record)

    def endorsement_proposal_exists(self, proposal_event_id: str) -> bool:
        return self.conn.execute(
            """
            SELECT 1
            FROM canonical_events
            WHERE event_id=?
              AND event_type=?
            """,
            (
                proposal_event_id,
                EventType.CANONICAL_ENDORSEMENT_PROPOSED.value,
            ),
        ).fetchone() is not None


# Canonical means canonical. No shadow table gets promoted because it is handy.
class EventLedger:
    """Append-only SQLite canonical event ledger.

    This is where the receipts live. The TransitionGate belongs to the ledger,
    so callers cannot swap in a permissive bouncer when nobody is looking.

    SQLite itself is not treated as an adversarial security boundary. Raw SQL
    with direct file access can still bypass application semantics. On open, the
    ledger verifies schema and the full hash chain; before each append it checks
    the current tail. A raw writer able to forge a fully consistent chain remains
    outside the Implementation 001.1 threat model. No fake invincibility claims.
    """

    _KNOWN_USER_TABLES = {"canonical_events"}
    _REQUIRED_TRIGGERS = {
        "canonical_events_no_update",
        "canonical_events_no_delete",
    }
    _EXPECTED_TRIGGER_SQL = {
        "canonical_events_no_update": """
            CREATE TRIGGER canonical_events_no_update
            BEFORE UPDATE ON canonical_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'canonical event ledger is append-only'
                );
            END
        """,
        "canonical_events_no_delete": """
            CREATE TRIGGER canonical_events_no_delete
            BEFORE DELETE ON canonical_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'canonical event ledger is append-only'
                );
            END
        """,
    }
    _EXPECTED_EVENT_COLUMNS = (
        "sequence",
        "event_id",
        "committed_at",
        "event_type",
        "actor_kind",
        "actor_id",
        "epistemic_class",
        "claim_domain",
        "payload_json",
        "ancestry_json",
        "causal_parent_ids_json",
        "content_restrictions_json",
        "renderer_mediated",
        "renderer_id",
        "policy_version",
        "idempotency_key",
        "proposal_hash",
        "prev_event_hash",
        "event_hash",
    )

    def __init__(
        self,
        path: str | Path,
        *,
        now_fn=None,
        verify_on_open: bool = True,
    ):
        self.path = str(path)
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._gate = TransitionGate(now_fn=self._now_fn)
        self._initialize()
        self.verify_schema()
        if verify_on_open:
            self.verify_integrity()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    def _initialize(self) -> None:
        """Create the canonical schema only for a genuinely empty database.

        Existing schema is evidence. Opening an existing ledger must not repair
        missing or altered integrity objects before verification can inspect
        them.
        """
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            existing = conn.execute(
                """
                SELECT 1
                FROM sqlite_schema
                WHERE name NOT LIKE 'sqlite_%'
                LIMIT 1
                """
            ).fetchone()
            if existing is not None:
                return

            conn.executescript(
                """
                CREATE TABLE canonical_events (
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
                    renderer_mediated INTEGER NOT NULL
                        CHECK(renderer_mediated IN (0,1)),
                    renderer_id TEXT,
                    policy_version TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    proposal_hash TEXT NOT NULL,
                    prev_event_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                );

                CREATE TRIGGER canonical_events_no_update
                BEFORE UPDATE ON canonical_events
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'canonical event ledger is append-only'
                    );
                END;

                CREATE TRIGGER canonical_events_no_delete
                BEFORE DELETE ON canonical_events
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'canonical event ledger is append-only'
                    );
                END;

                CREATE INDEX idx_event_type
                    ON canonical_events(event_type);

                CREATE INDEX idx_actor
                    ON canonical_events(actor_kind,actor_id);
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _verify_schema_conn(self, conn: sqlite3.Connection) -> None:
        table_rows = conn.execute(
            """
            SELECT name
            FROM sqlite_schema
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        actual_tables = {row["name"] for row in table_rows}
        if actual_tables != self._KNOWN_USER_TABLES:
            raise IntegrityError(
                "unacknowledged SQLite table set: "
                f"expected {sorted(self._KNOWN_USER_TABLES)}, "
                f"found {sorted(actual_tables)}"
            )

        trigger_rows = conn.execute(
            """
            SELECT name, sql
            FROM sqlite_schema
            WHERE type='trigger'
            ORDER BY name
            """
        ).fetchall()
        actual_triggers = {row["name"] for row in trigger_rows}
        if actual_triggers != self._REQUIRED_TRIGGERS:
            raise IntegrityError(
                "append-only trigger set drift: "
                f"expected {sorted(self._REQUIRED_TRIGGERS)}, "
                f"found {sorted(actual_triggers)}"
            )

        def normalize_sql(sql: str | None) -> str:
            return " ".join((sql or "").split()).rstrip(";").lower()

        actual_trigger_sql = {
            row["name"]: normalize_sql(row["sql"])
            for row in trigger_rows
        }
        for name, expected_sql in self._EXPECTED_TRIGGER_SQL.items():
            if actual_trigger_sql.get(name) != normalize_sql(expected_sql):
                raise IntegrityError(
                    f"append-only trigger definition drift: {name}"
                )

        column_rows = conn.execute(
            "PRAGMA table_info(canonical_events)"
        ).fetchall()
        actual_columns = tuple(row["name"] for row in column_rows)
        if actual_columns != self._EXPECTED_EVENT_COLUMNS:
            raise IntegrityError(
                "canonical_events schema drift: "
                f"expected {self._EXPECTED_EVENT_COLUMNS}, "
                f"found {actual_columns}"
            )

    def verify_schema(self) -> None:
        conn = self._connect()
        try:
            self._verify_schema_conn(conn)
        finally:
            conn.close()

    def get_event(self, event_id: str) -> EventRecord | None:
        conn = self._connect()
        try:
            return _TxView(conn).get_event(event_id)
        finally:
            conn.close()

    def get_event_by_sequence(
        self,
        sequence: int,
    ) -> EventRecord | None:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT *
                FROM canonical_events
                WHERE sequence=?
                """,
                (sequence,),
            ).fetchone()
            return _row_to_record(row) if row else None
        finally:
            conn.close()

    def head(self) -> EventRecord | None:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT *
                FROM canonical_events
                ORDER BY sequence DESC
                LIMIT 1
                """
            ).fetchone()
            return _row_to_record(row) if row else None
        finally:
            conn.close()

    def iter_events(
        self,
        *,
        after_sequence: int = 0,
        through_sequence: int | None = None,
    ) -> Iterator[EventRecord]:
        conn = self._connect()
        try:
            if through_sequence is None:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM canonical_events
                    WHERE sequence > ?
                    ORDER BY sequence
                    """,
                    (after_sequence,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM canonical_events
                    WHERE sequence > ?
                      AND sequence <= ?
                    ORDER BY sequence
                    """,
                    (after_sequence, through_sequence),
                ).fetchall()
        finally:
            conn.close()

        for row in rows:
            yield _row_to_record(row)

    def _verify_tail(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT *
            FROM canonical_events
            ORDER BY sequence DESC
            LIMIT 2
            """
        ).fetchall()

        if not rows:
            return

        try:
            latest = _row_to_record(rows[0])
            predecessor_hash = (
                _row_to_record(rows[1]).event_hash
                if len(rows) == 2
                else "GENESIS"
            )
        except Exception as exc:
            raise IntegrityError(
                f"tail contains unparsable canonical event: {exc}"
            ) from exc

        if latest.prev_event_hash != predecessor_hash:
            raise IntegrityError(
                "tail predecessor hash does not match previous event"
            )

        expected = hashlib.sha256(
            _canonical_json(_event_material(latest)).encode("utf-8")
        ).hexdigest()
        if latest.event_hash != expected:
            raise IntegrityError("tail event hash mismatch")

    def commit(
        self,
        proposal: EventProposal,
        *,
        event_id: str | None = None,
    ) -> EventRecord:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._verify_schema_conn(conn)
            self._verify_tail(conn)
            view = _TxView(conn)

            proposal_hash = _proposal_hash(proposal)

            if event_id is not None:
                row = conn.execute(
                    """
                    SELECT *
                    FROM canonical_events
                    WHERE event_id=?
                    """,
                    (event_id,),
                ).fetchone()
                if row is not None:
                    if row["proposal_hash"] != proposal_hash:
                        conn.rollback()
                        raise IdempotencyConflict(
                            "event_id reused for a different event proposal"
                        )
                    conn.rollback()
                    return _row_to_record(row)

            if proposal.idempotency_key:
                row = conn.execute(
                    """
                    SELECT *
                    FROM canonical_events
                    WHERE idempotency_key=?
                    """,
                    (proposal.idempotency_key,),
                ).fetchone()
                if row is not None:
                    if row["proposal_hash"] != proposal_hash:
                        conn.rollback()
                        raise IdempotencyConflict(
                            "idempotency key reused for a different "
                            "event proposal"
                        )
                    conn.rollback()
                    return _row_to_record(row)

            decision = self._gate.validate(proposal, view)
            if not decision.accepted:
                conn.rollback()
                raise GateRejected(decision)

            eid = event_id or str(uuid.uuid4())
            committed_dt = self._now_fn()
            if committed_dt.tzinfo is None:
                committed_dt = committed_dt.replace(tzinfo=timezone.utc)
            committed_at = committed_dt.astimezone(timezone.utc).isoformat()

            prev = conn.execute(
                """
                SELECT event_hash
                FROM canonical_events
                ORDER BY sequence DESC
                LIMIT 1
                """
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
                "ancestry": [
                    {"event_id": e.event_id, "mode": e.mode.value}
                    for e in proposal.ancestry
                ],
                "causal_parent_ids": list(proposal.causal_parent_ids),
                "content_restrictions": sorted(
                    r.value for r in proposal.content_restrictions
                ),
                "renderer_mediated": proposal.renderer_mediated,
                "renderer_id": proposal.renderer_id,
                "policy_version": proposal.policy_version,
                "idempotency_key": proposal.idempotency_key,
                "proposal_hash": proposal_hash,
                "prev_event_hash": prev_hash,
            }

            event_hash = hashlib.sha256(
                _canonical_json(material).encode("utf-8")
            ).hexdigest()

            cur = conn.execute(
                """
                INSERT INTO canonical_events(
                    event_id,
                    committed_at,
                    event_type,
                    actor_kind,
                    actor_id,
                    epistemic_class,
                    claim_domain,
                    payload_json,
                    ancestry_json,
                    causal_parent_ids_json,
                    content_restrictions_json,
                    renderer_mediated,
                    renderer_id,
                    policy_version,
                    idempotency_key,
                    proposal_hash,
                    prev_event_hash,
                    event_hash
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    eid,
                    committed_at,
                    proposal.event_type.value,
                    proposal.actor_kind.value,
                    proposal.actor_id,
                    proposal.epistemic_class.value,
                    proposal.claim_domain.value,
                    _canonical_json(dict(proposal.payload)),
                    _canonical_json(
                        [
                            {
                                "event_id": e.event_id,
                                "mode": e.mode.value,
                            }
                            for e in proposal.ancestry
                        ]
                    ),
                    _canonical_json(list(proposal.causal_parent_ids)),
                    _canonical_json(
                        sorted(
                            r.value
                            for r in proposal.content_restrictions
                        )
                    ),
                    1 if proposal.renderer_mediated else 0,
                    proposal.renderer_id,
                    proposal.policy_version,
                    proposal.idempotency_key,
                    proposal_hash,
                    prev_hash,
                    event_hash,
                ),
            )
            seq = cur.lastrowid
            conn.commit()

            row = conn.execute(
                """
                SELECT *
                FROM canonical_events
                WHERE sequence=?
                """,
                (seq,),
            ).fetchone()
            return _row_to_record(row)

        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def verify_integrity(self) -> None:
        prev_hash = "GENESIS"

        try:
            records = list(self.iter_events())
        except Exception as exc:
            raise IntegrityError(
                f"canonical ledger contains unparsable event: {exc}"
            ) from exc

        for record in records:
            if record.prev_event_hash != prev_hash:
                raise IntegrityError(
                    "predecessor hash mismatch at "
                    f"sequence {record.sequence}"
                )

            expected = hashlib.sha256(
                _canonical_json(_event_material(record)).encode("utf-8")
            ).hexdigest()

            if record.event_hash != expected:
                raise IntegrityError(
                    f"event hash mismatch at sequence {record.sequence}"
                )

            prev_hash = record.event_hash


def _row_to_record(row: sqlite3.Row) -> EventRecord:
    return EventRecord(
        event_id=row["event_id"],
        sequence=row["sequence"],
        committed_at=row["committed_at"],
        event_type=EventType(row["event_type"]),
        actor_kind=ActorKind(row["actor_kind"]),
        actor_id=row["actor_id"],
        epistemic_class=EpistemicClass(row["epistemic_class"]),
        claim_domain=ClaimDomain(row["claim_domain"]),
        payload=json.loads(row["payload_json"]),
        ancestry=tuple(
            AncestryEdge(
                x["event_id"],
                DerivationMode(x["mode"]),
            )
            for x in json.loads(row["ancestry_json"])
        ),
        causal_parent_ids=tuple(
            json.loads(row["causal_parent_ids_json"])
        ),
        content_restrictions=frozenset(
            Restriction(x)
            for x in json.loads(row["content_restrictions_json"])
        ),
        renderer_mediated=bool(row["renderer_mediated"]),
        renderer_id=row["renderer_id"],
        policy_version=row["policy_version"],
        idempotency_key=row["idempotency_key"],
        prev_event_hash=row["prev_event_hash"],
        event_hash=row["event_hash"],
    )
