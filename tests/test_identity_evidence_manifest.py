"""Synthetic bytes only, no real Kiki transcript or instructions."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.identity_evidence_manifest import EvidenceRejected, verify


class EvidenceManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {}
        for name, data in (("stimulus", b"sample question\n"),
                           ("instruction", b"sample instruction\n"),
                           ("response", b"sample answer\n")):
            (self.root / name).write_bytes(data)
            self.files[name] = {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
        self.manifest = {"schema": "kiki.choice-evidence.v1",
                         "observations": [{"id": "synthetic-1", **self.files}]}

    def test_three_files_verified(self):
        receipt = verify(self.manifest, self.root)
        self.assertEqual(receipt["verified_files"], 3)
        self.assertEqual(receipt["canonical_writes"], 0)

    def test_mutated_bytes_rejected(self):
        (self.root / "response").write_bytes(b"tampered")
        with self.assertRaisesRegex(EvidenceRejected, "evidence_hash_mismatch"):
            verify(self.manifest, self.root)

    def test_wrong_expected_hash_rejected(self):
        self.files["stimulus"]["sha256"] = "a" * 64
        with self.assertRaisesRegex(EvidenceRejected, "evidence_hash_mismatch"):
            verify(self.manifest, self.root)

    def test_absolute_path_rejected(self):
        self.files["stimulus"]["path"] = str(self.root / "stimulus")
        with self.assertRaisesRegex(EvidenceRejected, "invalid_relative_path"):
            verify(self.manifest, self.root)

    def test_parent_escape_rejected(self):
        self.files["stimulus"]["path"] = "../other"
        with self.assertRaisesRegex(EvidenceRejected, "invalid_relative_path"):
            verify(self.manifest, self.root)

    def test_missing_file_rejected(self):
        self.files["stimulus"]["path"] = "missing"
        with self.assertRaises((OSError, EvidenceRejected)):
            verify(self.manifest, self.root)

    def test_symlink_escape_rejected(self):
        with TemporaryDirectory() as outside:
            target = Path(outside) / "other"
            target.write_bytes(b"other")
            (self.root / "external").symlink_to(target)
            self.files["stimulus"]["path"] = "external"
            with self.assertRaisesRegex(EvidenceRejected, "evidence_path_outside_root_or_not_file"):
                verify(self.manifest, self.root)

    def test_duplicate_id_rejected(self):
        self.manifest["observations"].append(self.manifest["observations"][0].copy())
        with self.assertRaisesRegex(EvidenceRejected, "invalid_or_duplicate_observation_id"):
            verify(self.manifest, self.root)

    def test_nonstring_path_rejected(self):
        self.files["stimulus"]["path"] = ["stimulus"]
        with self.assertRaisesRegex(EvidenceRejected, "invalid_relative_path"):
            verify(self.manifest, self.root)

    def test_bad_schema_rejected(self):
        self.manifest["schema"] = "not-the-schema"
        with self.assertRaisesRegex(EvidenceRejected, "unsupported_manifest"):
            verify(self.manifest, self.root)

    def test_receipt_excludes_private_text_and_paths(self):
        r = str(verify(self.manifest, self.root))
        self.assertNotIn("sample question", r)
        self.assertNotIn("stimulus", r)
        self.assertNotIn(str(self.root), r)


if __name__ == "__main__":
    unittest.main()
