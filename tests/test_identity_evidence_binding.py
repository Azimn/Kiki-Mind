"""Synthetic binding tests. No private Kiki evidence is used."""
import copy
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.identity_evidence_binding import bind, BindingRejected


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {}
        for name, data in (("stimulus", b"fictional prompt"),
                           ("instruction", b"fictional instructions"),
                           ("response", b"fictional response")):
            (self.root / name).write_bytes(data)
            self.files[name] = {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
        self.manifest = {"schema": "kiki.choice-evidence.v1",
                         "observations": [{"id": "sample", **self.files}]}
        self.pack = {
            "schema": "kiki.choice-studio.v1",
            "scenes": [{"id": "scene", "domain": "aesthetics",
                        "choice_type": "bounded", "prompt": "Choose a style",
                        "tradeoff": "Charm versus maintenance",
                        "options": ["charm", "maintenance"],
                        "user_preference_disclosed": False}],
            "observations": [{
                "id": "sample", "scene_id": "scene",
                "implementation_id": "fake_impl", "model_id": "fake_model",
                "context_id": "synthetic_context",
                "recorded_at": "2026-11-16T10:00:00-06:00",
                "provenance": "renderer_output",
                "verification": "local_bytes_verified",
                "stimulus_sha256": self.files["stimulus"]["sha256"],
                "instruction_sha256": self.files["instruction"]["sha256"],
                "raw_response_sha256": self.files["response"]["sha256"],
                "source_ref": "private/sample",
                "choice": "charm", "reason": "I like bright colors.",
                "acknowledged_tradeoff": "It is harder to maintain.",
                "revision_condition": "If the finish wears away.",
                "explicit_rejection_of_options": False,
            }]
        }

    def test_valid_bound_evidence(self):
        receipt = bind(self.pack, self.manifest, self.root)
        self.assertEqual(receipt["bound_observations"], 1)
        self.assertEqual(receipt["verified_files"], 3)
        self.assertEqual(receipt["canonical_writes"], 0)

    def test_response_hash_mismatch(self):
        self.pack["observations"][0]["raw_response_sha256"] = "a" * 64
        with self.assertRaisesRegex(BindingRejected, "observation_hash_mismatch"):
            bind(self.pack, self.manifest, self.root)

    def test_instruction_hash_mismatch(self):
        self.pack["observations"][0]["instruction_sha256"] = "a" * 64
        with self.assertRaisesRegex(BindingRejected, "observation_hash_mismatch"):
            bind(self.pack, self.manifest, self.root)

    def test_stimulus_hash_mismatch(self):
        self.pack["observations"][0]["stimulus_sha256"] = "a" * 64
        with self.assertRaisesRegex(BindingRejected, "observation_hash_mismatch"):
            bind(self.pack, self.manifest, self.root)

    def test_tampered_original_bytes(self):
        (self.root / "response").write_bytes(b"tampered")
        with self.assertRaisesRegex(BindingRejected, "upstream_validation_failed"):
            bind(self.pack, self.manifest, self.root)

    def test_unpaired_manifest_id(self):
        self.manifest["observations"][0]["id"] = "different"
        with self.assertRaisesRegex(BindingRejected, "observation_id_mismatch"):
            bind(self.pack, self.manifest, self.root)

    def test_manifest_missing_observation(self):
        self.manifest["observations"] = []
        with self.assertRaisesRegex(BindingRejected, "upstream_validation_failed"):
            bind(self.pack, self.manifest, self.root)

    def test_observation_missing(self):
        self.pack["observations"] = []
        with self.assertRaisesRegex(BindingRejected, "observation_count_mismatch"):
            bind(self.pack, self.manifest, self.root)

    def test_connector_claim_not_local_verification(self):
        self.pack["observations"][0]["verification"] = "connector_readback"
        with self.assertRaisesRegex(BindingRejected, "unverified_observation_claim"):
            bind(self.pack, self.manifest, self.root)

    def test_unverified_not_accepted(self):
        self.pack["observations"][0]["verification"] = "unverified"
        with self.assertRaisesRegex(BindingRejected, "unverified_observation_claim"):
            bind(self.pack, self.manifest, self.root)

    def test_private_text_not_in_receipt(self):
        receipt = str(bind(self.pack, self.manifest, self.root))
        for sensitive in ("bright colors", "private/sample", "fake_impl",
                          str(self.root), "fictional"):
            self.assertNotIn(sensitive, receipt)

    def test_duplicate_manifest_rejected(self):
        self.manifest["observations"].append(copy.deepcopy(self.manifest["observations"][0]))
        with self.assertRaisesRegex(BindingRejected, "upstream_validation_failed"):
            bind(self.pack, self.manifest, self.root)


if __name__ == "__main__":
    unittest.main()
