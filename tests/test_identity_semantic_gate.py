import hashlib
import unittest
from tools.identity_semantic_gate import validate, AdjudicationRejected, FIELDS


def packet(response="I choose gold because it lasts."):
    finding = {"disposition": "supported", "spans": [{"start": 0, "end": 13, "text": "I choose gold"}]}
    return {"schema": "kiki.choice-adjudication.v1", "observation_id": "trial-1",
            "response_sha256": hashlib.sha256(response.encode()).hexdigest(),
            "reviews": [{"reviewer_id": str(i), "reviewed_at": "2026-11-16T20:00:00Z",
                         "fields": {name: dict(finding) for name in FIELDS}} for i in (1, 2)]}


class GateTests(unittest.TestCase):
    def test_valid_structural_receipt(self):
        self.assertTrue(validate(packet(), "I choose gold because it lasts.")["eligible_for_manual_review"])
    def test_tampered_response(self):
        with self.assertRaises(AdjudicationRejected): validate(packet(), "Changed")
    def test_duplicate_reviewer(self):
        p = packet(); p["reviews"][1]["reviewer_id"] = "1"
        with self.assertRaises(AdjudicationRejected): validate(p, "I choose gold because it lasts.")
    def test_false_span(self):
        p = packet(); p["reviews"][0]["fields"]["choice"]["spans"][0]["text"] = "fabricated"
        with self.assertRaises(AdjudicationRejected): validate(p, "I choose gold because it lasts.")
    def test_ambiguous_quarantined(self):
        p = packet(); p["reviews"][0]["fields"]["choice"] = {"disposition": "ambiguous", "spans": []}
        r = validate(p, "I choose gold because it lasts.")
        self.assertFalse(r["eligible_for_manual_review"])
        self.assertEqual(r["disputed_fields"], 1)
    def test_missing_evidence(self):
        p = packet(); p["reviews"][0]["fields"]["reason"]["spans"] = []
        with self.assertRaises(AdjudicationRejected): validate(p, "I choose gold because it lasts.")
    def test_bool_offsets_rejected(self):
        p = packet(); p["reviews"][0]["fields"]["reason"]["spans"][0]["start"] = True
        with self.assertRaises(AdjudicationRejected): validate(p, "I choose gold because it lasts.")


if __name__ == "__main__":
    unittest.main()
