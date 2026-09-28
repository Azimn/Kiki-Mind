"""Implementation 002 hostile probes.

Code knives stay out until the shadow brain proves it can be deleted, replayed,
caught lying, caught lagging, and rebuilt without touching canonical history.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest

from runtime.kiki_mind.ledger import EventLedger
from runtime.kiki_mind.models import (
    ActorKind,
    AncestryEdge,
    ClaimDomain,
    DerivationMode,
    EpistemicClass,
    EventProposal,
    EventType,
)
from runtime.kiki_mind.projection import (
    GENESIS_HASH,
    ProjectionBackwardsError,
    ProjectionCheckpointMismatch,
    ProjectionConflict,
    ProjectionCorruption,
    ProjectionDivergence,
    ProjectionImplementationMismatch,
    ProjectionRunner,
    ProjectionSchemaError,
    ProjectionSerializationError,
    ProjectionStore,
    ProjectionStoreSeparationError,
    ProjectionStaleError,
    ProjectionUnsafeReadError,
    ProjectionVersionMismatch,
)
from runtime.kiki_mind.projectors.accounting import (
    LedgerAccountingProjectorV1,
)
from runtime.kiki_mind.projectors.encounter_index import (
    EncounterIndexProjectorV1,
)


def canonical_json(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


class KikiMindImplementation002Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db = root / "mind.db"
        self.proj = root / "projection.db"
        self.now = datetime(
            2026, 9, 26, 21, 0, tzinfo=timezone.utc
        )
        self.ledger = EventLedger(
            self.db,
            now_fn=lambda: self.now,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def evidence(self, title="source"):
        return self.ledger.commit(
            EventProposal(
                event_type=EventType.EVIDENCE_INGESTED,
                actor_kind=ActorKind.SYSTEM,
                actor_id="test-import",
                epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
                claim_domain=ClaimDomain.EXTERNAL_FACT,
                payload={"title": title},
            )
        )

    def encounter(
        self,
        base,
        *,
        mode="design_history",
        version="count-activation-v1",
        encounter_type="retrieval",
    ):
        return self.ledger.commit(
            EventProposal(
                event_type=EventType.ENCOUNTER_RECORDED,
                actor_kind=ActorKind.KIKI,
                actor_id="kiki",
                epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
                ancestry=(
                    AncestryEdge(
                        base.event_id,
                        DerivationMode.CAUSAL_PARENT,
                    ),
                ),
                causal_parent_ids=(base.event_id,),
                payload={
                    "representation_id": base.event_id,
                    "encounter_type": encounter_type,
                    "mode": mode,
                    "activation_function_version": version,
                },
            )
        )

    def accounting_runner(self, *, store=None):
        return ProjectionRunner(
            self.ledger,
            self.proj,
            LedgerAccountingProjectorV1(),
            store=store,
            now_fn=lambda: self.now,
        )

    def test_explicit_genesis_projection(self):
        runner = self.accounting_runner()
        state = runner.run()
        snapshot = runner.store.load_unverified("ledger-accounting")

        self.assertEqual(state["event_count"], 0)
        self.assertEqual(snapshot.last_sequence, 0)
        self.assertEqual(snapshot.last_event_hash, GENESIS_HASH)

    def test_full_replay_builds_expected_state(self):
        self.evidence("a")
        self.evidence("b")
        runner = self.accounting_runner()

        state = runner.rebuild()

        self.assertEqual(state["event_count"], 2)
        self.assertEqual(
            state["event_type_counts"]["evidence.ingested"],
            2,
        )

    def test_delete_and_rebuild_is_identical(self):
        self.evidence("a")
        self.evidence("b")
        runner = self.accounting_runner()
        first = runner.run()

        runner.store.discard("ledger-accounting")
        second = runner.rebuild()

        self.assertEqual(
            canonical_json(first),
            canonical_json(second),
        )

    def test_incremental_equals_full_replay(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()
        self.evidence("b")
        incremental = runner.run()

        runner.store.discard("ledger-accounting")
        rebuilt = runner.rebuild()

        self.assertEqual(
            canonical_json(incremental),
            canonical_json(rebuilt),
        )

    def test_restart_resume_without_duplication(self):
        self.evidence("a")
        first_runner = self.accounting_runner()
        first_runner.run()
        self.evidence("b")

        second_runner = self.accounting_runner()
        state = second_runner.run()

        self.assertEqual(state["event_count"], 2)

    def test_projection_lags_until_rerun(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()
        self.evidence("b")

        with self.assertRaises(ProjectionStaleError):
            runner.current_verified()

        stale_prefix = runner.checkpoint_verified()
        caught_up = runner.run()

        self.assertEqual(stale_prefix["event_count"], 1)
        self.assertEqual(caught_up["event_count"], 2)
        self.assertEqual(
            runner.current_verified()["event_count"],
            2,
        )

    def test_partial_rebuild_is_explicitly_checkpoint_verified(self):
        self.evidence("a")
        self.evidence("b")
        runner = self.accounting_runner()

        partial = runner.rebuild(through_sequence=1)

        self.assertEqual(partial["event_count"], 1)
        self.assertEqual(
            runner.checkpoint_verified()["event_count"],
            1,
        )
        with self.assertRaises(ProjectionStaleError):
            runner.current_verified()

    def test_repair_does_not_launder_staleness_as_corruption(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()
        self.evidence("b")

        with self.assertRaises(ProjectionStaleError):
            runner.repair()

    def test_default_run_detects_head_advance_during_projection(self):
        class ConcurrentAppendStore(ProjectionStore):
            def __init__(store_self, path):
                store_self.appended = False
                super().__init__(path)

            def _before_commit(store_self, conn, snapshot):
                if snapshot.last_sequence > 0 and not store_self.appended:
                    store_self.appended = True
                    self.evidence("concurrent")

        self.evidence("a")
        store = ConcurrentAppendStore(self.proj)
        runner = self.accounting_runner(store=store)

        with self.assertRaises(ProjectionStaleError):
            runner.run()

        self.assertEqual(
            runner.checkpoint_verified()["event_count"],
            1,
        )
        caught_up = runner.run()
        self.assertEqual(caught_up["event_count"], 2)
        self.assertEqual(
            runner.current_verified()["event_count"],
            2,
        )

    def test_version_mismatch_refuses_incremental_continuation(self):
        self.evidence("a")
        self.accounting_runner().run()

        class AccountingV2(LedgerAccountingProjectorV1):
            name = "ledger-accounting"
            version = "2"

        runner = ProjectionRunner(
            self.ledger,
            self.proj,
            AccountingV2(),
        )
        with self.assertRaises(ProjectionVersionMismatch):
            runner.run()

    def test_projector_fingerprint_is_stable_across_processes(self):
        script = textwrap.dedent(
            """
            from runtime.kiki_mind.projection import projector_fingerprint

            class NestedProjector:
                name = "nested"
                version = "1"

                def initial_state(self):
                    return {"items": []}

                def apply(self, state, event):
                    values = [x + 1 for x in (1, 2, 3)]
                    return {"items": values}

            print(projector_fingerprint(NestedProjector()))
            """
        )

        first = subprocess.check_output(
            [sys.executable, "-c", script],
            text=True,
        ).strip()
        second = subprocess.check_output(
            [sys.executable, "-c", script],
            text=True,
        ).strip()

        self.assertEqual(first, second)

    def test_same_version_implementation_drift_is_rejected(self):
        self.evidence("a")
        self.accounting_runner().run()

        class ChangedAccounting:
            name = "ledger-accounting"
            version = "1"

            def initial_state(self):
                return {"different": 0}

            def apply(self, state, event):
                return {"different": int(state["different"]) + 2}

        runner = ProjectionRunner(
            self.ledger,
            self.proj,
            ChangedAccounting(),
        )
        with self.assertRaises(ProjectionImplementationMismatch):
            runner.current_verified()

    def test_state_hash_corruption_is_detected(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()

        conn = sqlite3.connect(self.proj)
        conn.execute(
            """
            UPDATE projection_state
            SET state_json='{}'
            WHERE projector_name='ledger-accounting'
            """
        )
        conn.commit()
        conn.close()

        with self.assertRaises(ProjectionCorruption):
            runner.current_verified()

    def test_validly_rehashed_invented_state_is_detected(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()

        invented = {"event_count": 999}
        payload = canonical_json(invented)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        conn = sqlite3.connect(self.proj)
        conn.execute(
            """
            UPDATE projection_state
            SET state_json=?, state_hash=?
            WHERE projector_name='ledger-accounting'
            """,
            (payload, digest),
        )
        conn.commit()
        conn.close()

        with self.assertRaises(ProjectionDivergence):
            runner.current_verified()

    def test_corrupt_projection_repairs_from_ledger(self):
        self.evidence("a")
        runner = self.accounting_runner()
        expected = runner.run()

        conn = sqlite3.connect(self.proj)
        conn.execute(
            """
            UPDATE projection_state
            SET state_json='{}'
            WHERE projector_name='ledger-accounting'
            """
        )
        conn.commit()
        conn.close()

        repaired = runner.repair()
        self.assertEqual(
            canonical_json(expected),
            canonical_json(repaired),
        )

    def test_checkpoint_cannot_point_beyond_ledger_tail(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()

        conn = sqlite3.connect(self.proj)
        conn.execute(
            """
            UPDATE projection_state
            SET last_sequence=99
            WHERE projector_name='ledger-accounting'
            """
        )
        conn.commit()
        conn.close()

        with self.assertRaises(ProjectionCheckpointMismatch):
            runner.current_verified()

    def test_checkpoint_event_hash_mismatch_is_detected(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()

        conn = sqlite3.connect(self.proj)
        conn.execute(
            """
            UPDATE projection_state
            SET last_event_hash='not-the-canonical-hash'
            WHERE projector_name='ledger-accounting'
            """
        )
        conn.commit()
        conn.close()

        with self.assertRaises(ProjectionCheckpointMismatch):
            runner.current_verified()

    def test_projector_never_appends_canonical_events(self):
        self.evidence("a")
        before = self.ledger.head()
        before_hash = before.event_hash

        runner = self.accounting_runner()
        runner.run()
        runner.rebuild()

        after = self.ledger.head()
        self.assertEqual(after.sequence, before.sequence)
        self.assertEqual(after.event_hash, before_hash)

    def test_same_file_for_ledger_and_projection_is_rejected(self):
        with self.assertRaises(ProjectionStoreSeparationError):
            ProjectionRunner(
                self.ledger,
                self.db,
                LedgerAccountingProjectorV1(),
            )

    def test_hardlink_alias_of_ledger_is_rejected(self):
        alias = self.db.with_name("projection-hardlink.db")
        os.link(self.db, alias)

        with self.assertRaises(ProjectionStoreSeparationError):
            ProjectionRunner(
                self.ledger,
                alias,
                LedgerAccountingProjectorV1(),
            )

    def test_ambiguous_store_load_is_refused(self):
        store = ProjectionStore(self.proj)

        with self.assertRaises(ProjectionUnsafeReadError):
            store.load("ledger-accounting")

    def test_unverified_store_read_names_its_weaker_contract(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()

        snapshot = runner.store.load_unverified("ledger-accounting")

        self.assertEqual(snapshot.last_sequence, 1)
        self.assertEqual(snapshot.state["event_count"], 1)
        self.assertEqual(
            runner.current_verified()["event_count"],
            1,
        )

    def test_unknown_projection_table_is_rejected(self):
        ProjectionStore(self.proj)
        conn = sqlite3.connect(self.proj)
        conn.execute("CREATE TABLE surprise_cache(x INTEGER)")
        conn.commit()
        conn.close()

        with self.assertRaises(ProjectionSchemaError):
            ProjectionStore(self.proj)

    def test_incremental_checkpoint_update_is_atomic(self):
        class FaultingStore(ProjectionStore):
            def _before_commit(self, conn, snapshot):
                if snapshot.last_sequence > 0:
                    raise RuntimeError("forced transaction failure")

        self.evidence("a")
        store = FaultingStore(self.proj)
        runner = self.accounting_runner(store=store)

        with self.assertRaisesRegex(
            RuntimeError,
            "forced transaction failure",
        ):
            runner.run()

        snapshot = ProjectionStore(self.proj).load_unverified(
            "ledger-accounting"
        )
        self.assertEqual(snapshot.last_sequence, 0)
        self.assertEqual(snapshot.last_event_hash, GENESIS_HASH)

    def test_stale_writer_compare_and_swap_is_rejected(self):
        self.evidence("a")
        runner = self.accounting_runner()
        runner.run()
        stale = runner.store.load_unverified("ledger-accounting")

        self.evidence("b")
        runner.run()

        with self.assertRaises(ProjectionConflict):
            runner.store.compare_and_swap(
                stale,
                expected_last_sequence=stale.last_sequence,
                expected_last_event_hash=stale.last_event_hash,
            )

    def test_non_json_projector_state_is_rejected(self):
        class BadProjector:
            name = "bad"
            version = "1"

            def initial_state(self):
                return {"bad": set([1])}

            def apply(self, state, event):
                return state

        runner = ProjectionRunner(
            self.ledger,
            self.proj,
            BadProjector(),
        )
        with self.assertRaises(ProjectionSerializationError):
            runner.run()

    def test_nondeterministic_projector_is_rejected(self):
        class Nondeterministic:
            name = "nondeterministic"
            version = "1"

            def __init__(self):
                self.counter = 0

            def initial_state(self):
                return {"value": 0}

            def apply(self, state, event):
                self.counter += 1
                return {"value": self.counter}

        self.evidence("a")
        runner = ProjectionRunner(
            self.ledger,
            self.proj,
            Nondeterministic(),
        )
        with self.assertRaises(ProjectionDivergence):
            runner.run()

    def test_backwards_incremental_projection_is_rejected(self):
        self.evidence("a")
        self.evidence("b")
        runner = self.accounting_runner()
        runner.run()

        with self.assertRaises(ProjectionBackwardsError):
            runner.run(through_sequence=1)

    def test_encounter_index_accounting_is_traceable(self):
        base = self.evidence("base")
        first = self.encounter(base)
        second = self.encounter(
            base,
            encounter_type="rehearsal",
        )
        self.encounter(
            base,
            version="count-activation-v2",
        )

        runner = ProjectionRunner(
            self.ledger,
            self.proj,
            EncounterIndexProjectorV1(),
        )
        state = runner.run()
        key = "\u001f".join(
            (
                base.event_id,
                "design_history",
                "count-activation-v1",
            )
        )
        entry = state["entries"][key]

        self.assertEqual(entry["encounter_count"], 2)
        self.assertEqual(entry["first_sequence"], first.sequence)
        self.assertEqual(entry["last_sequence"], second.sequence)
        self.assertEqual(
            entry["last_encounter_type"],
            "rehearsal",
        )
        self.assertEqual(
            entry["source_event_ids"],
            [first.event_id, second.event_id],
        )

    def test_invented_derived_entry_with_valid_hash_is_rejected(self):
        base = self.evidence("base")
        self.encounter(base)
        runner = ProjectionRunner(
            self.ledger,
            self.proj,
            EncounterIndexProjectorV1(),
        )
        runner.run()

        snapshot = runner.store.load_unverified("encounter-index")
        invented = dict(snapshot.state)
        invented["entries"] = dict(invented["entries"])
        invented["entries"]["fake"] = {
            "representation_id": "never-canonical",
            "mode": "fake",
            "activation_function_version": "fake",
            "encounter_count": 1,
            "first_sequence": 999,
            "last_sequence": 999,
            "last_encounter_type": "fake",
            "source_event_ids": ["not-an-event"],
        }
        payload = canonical_json(invented)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        conn = sqlite3.connect(self.proj)
        conn.execute(
            """
            UPDATE projection_state
            SET state_json=?, state_hash=?
            WHERE projector_name='encounter-index'
            """,
            (payload, digest),
        )
        conn.commit()
        conn.close()

        with self.assertRaises(ProjectionDivergence):
            runner.current_verified()

    def test_ledger_prefix_read_apis_are_stable(self):
        first = self.evidence("a")
        second = self.evidence("b")
        third = self.evidence("c")

        self.assertEqual(
            self.ledger.get_event_by_sequence(2).event_id,
            second.event_id,
        )
        self.assertEqual(self.ledger.head().event_id, third.event_id)
        self.assertEqual(
            [e.event_id for e in self.ledger.iter_events(
                after_sequence=1,
                through_sequence=2,
            )],
            [second.event_id],
        )
        self.assertEqual(first.sequence, 1)

    def test_twenty_thousand_events_replay_deterministically(self):
        for i in range(20000):
            self.evidence(str(i))

        runner = self.accounting_runner()
        incremental = runner.run()
        rebuilt = runner.rebuild()

        self.assertEqual(incremental["event_count"], 20000)
        self.assertEqual(
            canonical_json(incremental),
            canonical_json(rebuilt),
        )


if __name__ == "__main__":
    unittest.main()
