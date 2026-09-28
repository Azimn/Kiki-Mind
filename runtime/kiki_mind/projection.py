"""Disposable state for Kiki Mind, also known as the shadow brain on a leash.

Projectors are allowed to summarize canonical history. They are not allowed to
become history. If a projection cannot be deleted, replayed, and challenged,
then it has gotten way too comfortable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import sqlite3
from types import CodeType
from typing import Any, Mapping, Protocol

from .ledger import EventLedger
from .models import EventRecord


DERIVED_CANONICALITY = "derived_disposable"
GENESIS_HASH = "GENESIS"


class ProjectionError(RuntimeError):
    pass


class ProjectionSchemaError(ProjectionError):
    pass


class ProjectionCorruption(ProjectionError):
    pass


class ProjectionCheckpointMismatch(ProjectionError):
    pass


class ProjectionVersionMismatch(ProjectionError):
    pass


class ProjectionImplementationMismatch(ProjectionError):
    pass


class ProjectionConflict(ProjectionError):
    pass


class ProjectionDivergence(ProjectionError):
    pass


class ProjectionSerializationError(ProjectionError):
    pass


class ProjectionStoreSeparationError(ProjectionError):
    pass


class ProjectionBackwardsError(ProjectionError):
    pass


class ProjectionStaleError(ProjectionError):
    pass


class ProjectionUnsafeReadError(ProjectionError):
    pass


class Projector(Protocol):
    name: str
    version: str

    def initial_state(self) -> Mapping[str, Any]:
        ...

    def apply(
        self,
        state: Mapping[str, Any],
        event: EventRecord,
    ) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class ProjectionSnapshot:
    projector_name: str
    projector_version: str
    projector_fingerprint: str
    state: Mapping[str, Any]
    state_hash: str
    last_sequence: int
    last_event_hash: str
    updated_at: str
    canonicality: str = DERIVED_CANONICALITY


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ProjectionSerializationError(
            f"projector state is not canonical JSON: {exc}"
        ) from exc


def _normalize_state(value: Mapping[str, Any]) -> dict[str, Any]:
    encoded = _canonical_json(value)
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        raise ProjectionSerializationError(
            "projector state must serialize to a JSON object"
        )
    return decoded


def _state_hash(state: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        _canonical_json(state).encode("utf-8")
    ).hexdigest()


def _constant_material(value: Any) -> Any:
    """Serialize Python code constants without process-specific repr noise."""
    if value is None:
        return {"type": "none"}
    if value is Ellipsis:
        return {"type": "ellipsis"}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "int", "value": value}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    if isinstance(value, complex):
        return {
            "type": "complex",
            "real": value.real,
            "imag": value.imag,
        }
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, bytes):
        return {"type": "bytes", "hex": value.hex()}
    if isinstance(value, tuple):
        return {
            "type": "tuple",
            "items": [_constant_material(item) for item in value],
        }
    if isinstance(value, frozenset):
        items = [_constant_material(item) for item in value]
        return {
            "type": "frozenset",
            "items": sorted(items, key=_canonical_json),
        }
    if isinstance(value, CodeType):
        return {
            "type": "code",
            "argcount": value.co_argcount,
            "posonlyargcount": value.co_posonlyargcount,
            "kwonlyargcount": value.co_kwonlyargcount,
            "nlocals": value.co_nlocals,
            "stacksize": value.co_stacksize,
            "flags": value.co_flags,
            "bytecode": value.co_code.hex(),
            "constants": [
                _constant_material(item) for item in value.co_consts
            ],
            "names": list(value.co_names),
            "varnames": list(value.co_varnames),
            "freevars": list(value.co_freevars),
            "cellvars": list(value.co_cellvars),
        }
    return {
        "type": f"{type(value).__module__}.{type(value).__qualname__}",
        "repr": repr(value),
    }


def _method_material(method: Any) -> dict[str, Any]:
    function = getattr(method, "__func__", method)
    code = getattr(function, "__code__", None)
    if code is None:
        return {"repr": repr(function)}

    defaults = getattr(function, "__defaults__", None)
    kwdefaults = getattr(function, "__kwdefaults__", None)
    return {
        "code": _constant_material(code),
        "defaults": _constant_material(defaults),
        "kwdefaults": (
            {
                key: _constant_material(value)
                for key, value in sorted(kwdefaults.items())
            }
            if kwdefaults
            else None
        ),
    }


def projector_fingerprint(projector: Projector) -> str:
    cls = projector.__class__
    material: dict[str, Any] = {
        "class": f"{cls.__module__}.{cls.__qualname__}",
        "name": projector.name,
        "version": projector.version,
        "initial_state": _method_material(projector.initial_state),
        "apply": _method_material(projector.apply),
    }

    try:
        source_path = inspect.getsourcefile(cls)
    except (OSError, TypeError):
        source_path = None

    if source_path:
        path = Path(source_path)
        if path.is_file():
            material["source_sha256"] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

    return hashlib.sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()


class ProjectionStore:
    _KNOWN_USER_TABLES = {"projection_state"}
    _EXPECTED_TABLE_SQL = """
        CREATE TABLE projection_state (
            projector_name TEXT PRIMARY KEY,
            projector_version TEXT NOT NULL,
            projector_fingerprint TEXT NOT NULL,
            state_json TEXT NOT NULL,
            state_hash TEXT NOT NULL,
            last_sequence INTEGER NOT NULL
                CHECK(last_sequence >= 0),
            last_event_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            canonicality TEXT NOT NULL
                CHECK(canonicality='derived_disposable')
        )
    """
    _EXPECTED_COLUMNS = (
        "projector_name",
        "projector_version",
        "projector_fingerprint",
        "state_json",
        "state_hash",
        "last_sequence",
        "last_event_hash",
        "updated_at",
        "canonicality",
    )

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._initialize()
        self.verify_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    def _initialize(self) -> None:
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

            conn.execute(self._EXPECTED_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()

    def _verify_schema_conn(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_schema
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        actual = {row["name"] for row in rows}
        if actual != self._KNOWN_USER_TABLES:
            raise ProjectionSchemaError(
                "unacknowledged projection table set: "
                f"expected {sorted(self._KNOWN_USER_TABLES)}, "
                f"found {sorted(actual)}"
            )

        table_row = conn.execute(
            """
            SELECT sql
            FROM sqlite_schema
            WHERE type='table'
              AND name='projection_state'
            """
        ).fetchone()
        if table_row is None:
            raise ProjectionSchemaError(
                "projection_state table definition is missing"
            )

        def normalize_sql(sql: str | None) -> str:
            return " ".join((sql or "").split()).rstrip(";").lower()

        if normalize_sql(table_row["sql"]) != normalize_sql(
            self._EXPECTED_TABLE_SQL
        ):
            raise ProjectionSchemaError(
                "projection_state table definition drift"
            )

        columns = conn.execute(
            "PRAGMA table_info(projection_state)"
        ).fetchall()
        actual_columns = tuple(row["name"] for row in columns)
        if actual_columns != self._EXPECTED_COLUMNS:
            raise ProjectionSchemaError(
                "projection_state schema drift: "
                f"expected {self._EXPECTED_COLUMNS}, "
                f"found {actual_columns}"
            )

    def verify_schema(self) -> None:
        conn = self._connect()
        try:
            self._verify_schema_conn(conn)
        finally:
            conn.close()

    def _row_to_snapshot(self, row: sqlite3.Row) -> ProjectionSnapshot:
        try:
            state = json.loads(row["state_json"])
        except Exception as exc:
            raise ProjectionCorruption(
                f"projection state JSON is invalid: {exc}"
            ) from exc
        if not isinstance(state, dict):
            raise ProjectionCorruption(
                "projection state JSON is not an object"
            )
        if row["canonicality"] != DERIVED_CANONICALITY:
            raise ProjectionCorruption(
                "projection canonicality marker is invalid"
            )
        if _state_hash(state) != row["state_hash"]:
            raise ProjectionCorruption(
                "projection state checksum mismatch"
            )
        return ProjectionSnapshot(
            projector_name=row["projector_name"],
            projector_version=row["projector_version"],
            projector_fingerprint=row["projector_fingerprint"],
            state=state,
            state_hash=row["state_hash"],
            last_sequence=row["last_sequence"],
            last_event_hash=row["last_event_hash"],
            updated_at=row["updated_at"],
            canonicality=row["canonicality"],
        )

    def load_unverified(
        self,
        projector_name: str,
    ) -> ProjectionSnapshot | None:
        """Read stored projection bytes without granting epistemic authority.

        This validates storage shape, the disposable marker, and the state
        checksum. It does NOT prove replay equivalence, freshness, or canonical
        authority. Think fitting-room mirror, not passport.
        """
        conn = self._connect()
        try:
            self._verify_schema_conn(conn)
            row = conn.execute(
                """
                SELECT *
                FROM projection_state
                WHERE projector_name=?
                """,
                (projector_name,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_snapshot(row)
        finally:
            conn.close()

    def load(
        self,
        projector_name: str,
    ) -> ProjectionSnapshot | None:
        """Refuse ambiguous projection reads.

        The old name was too easy to mistake for an authoritative state read.
        Use load_unverified() for explicit storage inspection, or use a
        ProjectionRunner verification method for state consumption.
        """
        raise ProjectionUnsafeReadError(
            "ProjectionStore.load() is intentionally unsafe and disabled; "
            "use load_unverified() for storage inspection, or "
            "ProjectionRunner.checkpoint_verified()/current_verified() "
            "for replay-verified state"
        )

    def initialize(self, snapshot: ProjectionSnapshot) -> None:
        if snapshot.last_sequence != 0:
            raise ProjectionConflict(
                "initial projection checkpoint must be GENESIS"
            )
        if snapshot.last_event_hash != GENESIS_HASH:
            raise ProjectionConflict(
                "initial projection hash must be GENESIS"
            )

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._verify_schema_conn(conn)
            exists = conn.execute(
                """
                SELECT 1
                FROM projection_state
                WHERE projector_name=?
                """,
                (snapshot.projector_name,),
            ).fetchone()
            if exists is not None:
                conn.rollback()
                return
            self._insert_snapshot(conn, snapshot)
            self._before_commit(conn, snapshot)
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def compare_and_swap(
        self,
        snapshot: ProjectionSnapshot,
        *,
        expected_last_sequence: int,
        expected_last_event_hash: str,
    ) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._verify_schema_conn(conn)
            cur = conn.execute(
                """
                UPDATE projection_state
                SET projector_version=?,
                    projector_fingerprint=?,
                    state_json=?,
                    state_hash=?,
                    last_sequence=?,
                    last_event_hash=?,
                    updated_at=?,
                    canonicality=?
                WHERE projector_name=?
                  AND last_sequence=?
                  AND last_event_hash=?
                """,
                (
                    snapshot.projector_version,
                    snapshot.projector_fingerprint,
                    _canonical_json(snapshot.state),
                    snapshot.state_hash,
                    snapshot.last_sequence,
                    snapshot.last_event_hash,
                    snapshot.updated_at,
                    snapshot.canonicality,
                    snapshot.projector_name,
                    expected_last_sequence,
                    expected_last_event_hash,
                ),
            )
            if cur.rowcount != 1:
                conn.rollback()
                raise ProjectionConflict(
                    "stale projection checkpoint"
                )
            self._before_commit(conn, snapshot)
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def replace(self, snapshot: ProjectionSnapshot) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._verify_schema_conn(conn)
            conn.execute(
                "DELETE FROM projection_state WHERE projector_name=?",
                (snapshot.projector_name,),
            )
            self._insert_snapshot(conn, snapshot)
            self._before_commit(conn, snapshot)
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def discard(self, projector_name: str) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._verify_schema_conn(conn)
            conn.execute(
                "DELETE FROM projection_state WHERE projector_name=?",
                (projector_name,),
            )
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def _insert_snapshot(
        self,
        conn: sqlite3.Connection,
        snapshot: ProjectionSnapshot,
    ) -> None:
        conn.execute(
            """
            INSERT INTO projection_state(
                projector_name,
                projector_version,
                projector_fingerprint,
                state_json,
                state_hash,
                last_sequence,
                last_event_hash,
                updated_at,
                canonicality
            )
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                snapshot.projector_name,
                snapshot.projector_version,
                snapshot.projector_fingerprint,
                _canonical_json(snapshot.state),
                snapshot.state_hash,
                snapshot.last_sequence,
                snapshot.last_event_hash,
                snapshot.updated_at,
                snapshot.canonicality,
            ),
        )

    def _before_commit(
        self,
        conn: sqlite3.Connection,
        snapshot: ProjectionSnapshot,
    ) -> None:
        """Test seam for proving transactional rollback."""
        return None


class ProjectionRunner:
    def __init__(
        self,
        ledger: EventLedger,
        projection_path: str | Path,
        projector: Projector,
        *,
        store: ProjectionStore | None = None,
        now_fn=None,
    ):
        ledger_path = Path(ledger.path).resolve()
        projection_resolved = Path(projection_path).resolve()

        same_physical_file = False
        if ledger_path.exists() and projection_resolved.exists():
            try:
                same_physical_file = ledger_path.samefile(
                    projection_resolved
                )
            except OSError:
                same_physical_file = False

        if ledger_path == projection_resolved or same_physical_file:
            raise ProjectionStoreSeparationError(
                "canonical ledger and projection store must be separate "
                "physical files"
            )

        self.ledger = ledger
        self.projector = projector
        self.projection_path = str(projection_path)
        self.store = store or ProjectionStore(projection_path)
        if Path(self.store.path).resolve() != projection_resolved:
            raise ProjectionStoreSeparationError(
                "provided projection store path does not match runner path"
            )
        self._now_fn = now_fn or (
            lambda: datetime.now(timezone.utc)
        )
        self._fingerprint = projector_fingerprint(projector)

    def _timestamp(self) -> str:
        value = self._now_fn()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()

    def _snapshot(
        self,
        state: Mapping[str, Any],
        *,
        last_sequence: int,
        last_event_hash: str,
    ) -> ProjectionSnapshot:
        normalized = _normalize_state(state)
        return ProjectionSnapshot(
            projector_name=self.projector.name,
            projector_version=self.projector.version,
            projector_fingerprint=self._fingerprint,
            state=normalized,
            state_hash=_state_hash(normalized),
            last_sequence=last_sequence,
            last_event_hash=last_event_hash,
            updated_at=self._timestamp(),
        )

    def _target_sequence(
        self,
        through_sequence: int | None,
    ) -> int:
        head = self.ledger.head()
        head_sequence = head.sequence if head is not None else 0
        if through_sequence is None:
            return head_sequence
        if through_sequence < 0:
            raise ProjectionCheckpointMismatch(
                "projection target cannot be negative"
            )
        if through_sequence > head_sequence:
            raise ProjectionCheckpointMismatch(
                "projection target is beyond canonical ledger head"
            )
        return through_sequence

    def _validate_snapshot(
        self,
        snapshot: ProjectionSnapshot,
    ) -> None:
        if snapshot.projector_version != self.projector.version:
            raise ProjectionVersionMismatch(
                "stored projector version does not match runner"
            )
        if snapshot.projector_fingerprint != self._fingerprint:
            raise ProjectionImplementationMismatch(
                "stored projector implementation fingerprint does not "
                "match runner"
            )
        if snapshot.last_sequence == 0:
            if snapshot.last_event_hash != GENESIS_HASH:
                raise ProjectionCheckpointMismatch(
                    "GENESIS checkpoint has a non-GENESIS hash"
                )
            return

        event = self.ledger.get_event_by_sequence(
            snapshot.last_sequence
        )
        if event is None:
            raise ProjectionCheckpointMismatch(
                "projection checkpoint is beyond or outside canonical ledger"
            )
        if event.event_hash != snapshot.last_event_hash:
            raise ProjectionCheckpointMismatch(
                "projection checkpoint event hash mismatch"
            )

    # The boring wall test: same ledger prefix, same projector, same state.
    # Anything else means hidden state snuck into the dressing room.
    def _replay(self, through_sequence: int) -> dict[str, Any]:
        state = _normalize_state(self.projector.initial_state())
        for event in self.ledger.iter_events(
            after_sequence=0,
            through_sequence=through_sequence,
        ):
            input_state = json.loads(_canonical_json(state))
            state = _normalize_state(
                self.projector.apply(input_state, event)
            )
        return state

    def _assert_replay_equivalent(
        self,
        snapshot: ProjectionSnapshot,
    ) -> dict[str, Any]:
        first = self._replay(snapshot.last_sequence)
        second = self._replay(snapshot.last_sequence)
        if _canonical_json(first) != _canonical_json(second):
            raise ProjectionDivergence(
                "projector is nondeterministic under zero-based replay"
            )
        if _canonical_json(first) != _canonical_json(snapshot.state):
            raise ProjectionDivergence(
                "stored projection does not equal deterministic replay "
                "of its claimed canonical prefix"
            )
        return first

    def _load_or_initialize(self) -> ProjectionSnapshot:
        snapshot = self.store.load_unverified(self.projector.name)
        if snapshot is not None:
            return snapshot

        genesis = self._snapshot(
            self.projector.initial_state(),
            last_sequence=0,
            last_event_hash=GENESIS_HASH,
        )
        self.store.initialize(genesis)
        loaded = self.store.load_unverified(self.projector.name)
        if loaded is None:
            raise ProjectionConflict(
                "projection GENESIS initialization did not persist"
            )
        return loaded

    # Verified and current are different accessories. Never mix them up.
    def _verified_snapshot(
        self,
    ) -> tuple[ProjectionSnapshot, dict[str, Any]]:
        self.ledger.verify_schema()
        self.ledger.verify_integrity()
        snapshot = self.store.load_unverified(self.projector.name)
        if snapshot is None:
            raise ProjectionCheckpointMismatch(
                "projection has not been built"
            )
        self._validate_snapshot(snapshot)
        state = self._assert_replay_equivalent(snapshot)
        return snapshot, state

    def checkpoint_verified(self) -> dict[str, Any]:
        """Return replay-verified state at its declared canonical prefix.

        This method proves equivalence to the checkpoint the projection claims.
        It does not claim that checkpoint is the current canonical ledger head.
        """
        _, state = self._verified_snapshot()
        return state

    def _assert_current_checkpoint(
        self,
        snapshot: ProjectionSnapshot,
        *,
        context: str,
    ) -> None:
        head = self.ledger.head()
        head_sequence = head.sequence if head is not None else 0
        head_hash = head.event_hash if head is not None else GENESIS_HASH

        if snapshot.last_sequence != head_sequence:
            raise ProjectionStaleError(
                f"{context}: projection is replay-valid for sequence "
                f"{snapshot.last_sequence} but canonical head is "
                f"{head_sequence}"
            )
        if snapshot.last_event_hash != head_hash:
            raise ProjectionCheckpointMismatch(
                f"{context}: projection head hash does not match "
                "canonical ledger head"
            )

    def current_verified(self) -> dict[str, Any]:
        """Return replay-verified state only when it is at ledger head."""
        snapshot, state = self._verified_snapshot()
        self._assert_current_checkpoint(
            snapshot,
            context="current verification",
        )
        return state

    def run(
        self,
        *,
        through_sequence: int | None = None,
    ) -> dict[str, Any]:
        self.ledger.verify_schema()
        self.ledger.verify_integrity()
        target = self._target_sequence(through_sequence)
        snapshot = self._load_or_initialize()
        self._validate_snapshot(snapshot)
        state = self._assert_replay_equivalent(snapshot)

        if target < snapshot.last_sequence:
            raise ProjectionBackwardsError(
                "incremental projection cannot move a checkpoint backward"
            )

        for event in self.ledger.iter_events(
            after_sequence=snapshot.last_sequence,
            through_sequence=target,
        ):
            input_state = json.loads(_canonical_json(state))
            state = _normalize_state(
                self.projector.apply(input_state, event)
            )
            next_snapshot = self._snapshot(
                state,
                last_sequence=event.sequence,
                last_event_hash=event.event_hash,
            )
            self.store.compare_and_swap(
                next_snapshot,
                expected_last_sequence=snapshot.last_sequence,
                expected_last_event_hash=snapshot.last_event_hash,
            )
            snapshot = next_snapshot

        saved = self.store.load_unverified(self.projector.name)
        if saved is None:
            raise ProjectionConflict(
                "projection disappeared during run"
            )
        self._validate_snapshot(saved)
        if saved.last_sequence != target:
            raise ProjectionConflict(
                "projection did not reach requested canonical prefix"
            )
        state = self._assert_replay_equivalent(saved)
        if through_sequence is None:
            self._assert_current_checkpoint(
                saved,
                context="projection run",
            )
        return state

    def rebuild(
        self,
        *,
        through_sequence: int | None = None,
    ) -> dict[str, Any]:
        self.ledger.verify_schema()
        self.ledger.verify_integrity()
        target = self._target_sequence(through_sequence)
        first = self._replay(target)
        second = self._replay(target)
        if _canonical_json(first) != _canonical_json(second):
            raise ProjectionDivergence(
                "projector is nondeterministic under zero-based replay"
            )
        if target == 0:
            event_hash = GENESIS_HASH
        else:
            event = self.ledger.get_event_by_sequence(target)
            if event is None:
                raise ProjectionCheckpointMismatch(
                    "rebuild target is not a canonical event"
                )
            event_hash = event.event_hash
        snapshot = self._snapshot(
            first,
            last_sequence=target,
            last_event_hash=event_hash,
        )
        self.store.replace(snapshot)
        saved = self.store.load_unverified(self.projector.name)
        if saved is None:
            raise ProjectionConflict(
                "projection disappeared during rebuild"
            )
        self._validate_snapshot(saved)
        if saved.last_sequence != target:
            raise ProjectionConflict(
                "rebuilt projection did not reach requested canonical prefix"
            )
        state = self._assert_replay_equivalent(saved)
        if through_sequence is None:
            self._assert_current_checkpoint(
                saved,
                context="projection rebuild",
            )
        return state

    # Repair rebuilds disposable state from history. It never repairs history
    # from disposable state. That direction would be, like, catastrophically gross.
    def repair(self) -> dict[str, Any]:
        try:
            return self.current_verified()
        except (
            ProjectionCorruption,
            ProjectionCheckpointMismatch,
            ProjectionDivergence,
        ):
            return self.rebuild()
