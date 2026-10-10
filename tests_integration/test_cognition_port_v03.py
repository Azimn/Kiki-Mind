"""v0.3 synthetic-only content gate tests; not independent cognition evidence."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from experiments.cognition_port_v03.run import (
    FIXTURE, create_ledger, trial,
)
from experiments.cognition_port_v03.source import (
    AuthorizedSyntheticContentSource, SyntheticSourceViolation, NAMESPACE,
)
from runtime.kiki_mind.ledger import EventLedger


class KikiContentPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.first = trial(cls.fixture, ledger_path=root / "first.db")
        cls.second = trial(cls.fixture, ledger_path=root / "second.db")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_precommitted_scope_is_36_cases_and_fiction_only(self):
        x = self.fixture
        self.assertEqual(x["classification"], "synthetic-public-fixture-only")
        self.assertFalse(x["independent_blinding"])
        self.assertEqual(len(x["tasks"]), 36)
        self.assertEqual(len({d["id"] for d in x["documents"]}), len(x["documents"]))
        self.assertEqual(sum(t["split"] == "development" for t in x["tasks"]), 18)
        self.assertEqual(sum(t["split"] == "evaluation" for t in x["tasks"]), 18)

    def test_original_source_scope_remains_separate(self):
        self.assertTrue(self.first["shared_direct_parity"])
        self.assertTrue(self.first["conclusions_limited_to_engineering_pilot"])
        self.assertFalse(self.first["independently_blinded"])
        self.assertTrue(self.first["oracle_intent_parsing"])
        self.assertFalse(self.first["model_inference"])
        self.assertEqual(len(self.first["cases"]["shared_port"]), 36)
        for d, p in zip(self.first["cases"]["direct_index"],
                        self.first["cases"]["shared_port"]):
            self.assertEqual((d["answer"], d["support_ids"]),
                             (p["answer"], p["support_ids"]))
        self.assertTrue(all(self.first["probes"].values()))

    def test_source_ids_never_cross_owner_or_restrictions(self):
        forbidden = {"D21", "D22"}
        for condition, rows in self.first["cases"].items():
            for case in rows:
                self.assertTrue(forbidden.isdisjoint(case["received_ids"]))
                self.assertTrue(forbidden.isdisjoint(case["support_ids"]))
        self.assertNotIn("secret_room", json.dumps(self.first))
        self.assertEqual(self.first["probes"], {
            "wrong_owner_denied": True,
            "restricted_hidden": True,
            "foreign_hidden": True,
            "revoked_denied": True,
            "stale_denied": True,
        })

    def test_same_synthetic_records_replay_exactly_without_timing_dependency(self):
        self.assertEqual(self.first["canonical_head_sha256"],
                         self.second["canonical_head_sha256"])
        self.assertEqual(self.first["corpus_logical_sha256"],
                         self.second["corpus_logical_sha256"])
        for arm in self.first["cases"]:
            self.assertEqual(self.first["cases"][arm], self.second["cases"][arm])

    def test_forged_sidecar_document_fails_source_hash_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = EventLedger(
                Path(directory) / "fixture.db",
                now_fn=lambda: datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc),
            )
            create_ledger(ledger, self.fixture)
            forged = deepcopy(self.fixture)
            forged["documents"][0]["claim"]["value"] = "intruder"
            with self.assertRaises(SyntheticSourceViolation):
                AuthorizedSyntheticContentSource(ledger, forged)

    def test_restricted_and_wrong_owner_fail_before_search(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = EventLedger(
                Path(directory) / "fixture.db",
                now_fn=lambda: datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc),
            )
            create_ledger(ledger, self.fixture)
            source = AuthorizedSyntheticContentSource(ledger, self.fixture)
            self.assertEqual(source.descriptor.subject_id, "kiki")
            self.assertEqual(source.descriptor.namespace, NAMESPACE)
            self.assertIsNone(source.get("D21"))
            self.assertIsNone(source.get("D22"))
            self.assertTrue(all(
                x.record_id not in ("D21", "D22")
                for x in source.search("prism sealed_map", top_k=20)
            ))


if __name__ == "__main__":
    unittest.main()
