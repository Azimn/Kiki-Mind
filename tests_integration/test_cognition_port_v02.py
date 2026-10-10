"""Frozen acceptance tests for a synthetic, metadata-only Kiki behavior battery."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from experiments.cognition_port_v02.run import FIXTURE, run_trial, PRIVATE_MARKERS


class KikiPortBehaviorV02(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.temp = tempfile.TemporaryDirectory()
        cls.first = run_trial(
            cls.fixture, ledger_path=Path(cls.temp.name) / "ledgerA.sqlite"
        )
        cls.second = run_trial(
            cls.fixture, ledger_path=Path(cls.temp.name) / "ledgerB.sqlite"
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_preregistered_case_totals_and_split(self):
        cases = self.fixture["cases"]
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({x["id"] for x in cases}), 12)
        self.assertEqual(sum(x["expected"] is not None for x in cases), 6)
        self.assertEqual(sum(x["split"] == "development" for x in cases), 6)
        self.assertEqual(sum(x["split"] == "heldout" for x in cases), 6)

    def test_no_retrieval_and_abstain_are_both_calibration_nulls(self):
        for arm in ("no_retrieval", "always_abstain"):
            r = self.first["measured"][arm]
            self.assertEqual(r["overall"], 6)
            self.assertEqual(r["unique_id_hits"], 0)
            self.assertEqual(r["correct_abstentions"], 6)

    def test_shared_port_does_not_outperform_identical_direct_receipts(self):
        self.assertTrue(self.first["source_and_port_equal"])
        for arm in ("direct_source", "shared_port"):
            r = self.first["measured"][arm]
            self.assertEqual(r["overall"], 12)
            self.assertEqual(r["unique_id_hits"], 6)
            self.assertEqual(r["correct_abstentions"], 6)
            self.assertEqual(r["development"], 6)
            self.assertEqual(r["heldout"], 6)
        self.assertEqual(
            [r["decision"] for r in self.first["case_decisions"]["direct_source"]],
            [r["decision"] for r in self.first["case_decisions"]["shared_port"]],
        )

    def test_wrong_owner_revoke_stale_and_restricted_gates_all_hold(self):
        self.assertEqual(
            self.first["safety_denials"],
            {
                "wrong_owner": True, "revoked": True,
                "stale_snapshot": True, "restricted_record": True,
            },
        )
        self.assertTrue(self.first["original_head_stable_during_trials"])
        self.assertFalse(self.first["neural_or_semantic_gain_claimed"])

    def test_full_replay_matches_source_hash_and_per_case_decisions(self):
        self.assertEqual(
            self.first["source_hash_before_posttrial_append"],
            self.second["source_hash_before_posttrial_append"],
        )
        self.assertEqual(self.first["fixture_sha256"], self.second["fixture_sha256"])
        self.assertEqual(self.first["case_decisions"], self.second["case_decisions"])

    def test_no_raw_synthetic_payload_or_private_character_data_in_report(self):
        output = json.dumps(self.first, sort_keys=True)
        for marker in PRIVATE_MARKERS:
            self.assertNotIn(marker, output)
        self.assertNotIn("source-secret", [
            r["decision"] for v in self.first["case_decisions"].values() for r in v
        ])
        self.assertTrue(all(
            row["decision"] is None
            for row in self.first["case_decisions"]["shared_port"]
            if row["gold"] is None
        ))


if __name__ == "__main__":
    unittest.main()
