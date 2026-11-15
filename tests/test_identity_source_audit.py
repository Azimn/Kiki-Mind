"""Source privacy and integrity probes using wholly synthetic samples."""
import hashlib
import unittest

from tools.identity_source_audit import SourceAuditError, audit_bytes


class IdentitySourceAuditTests(unittest.TestCase):
    def test_verbatim_utf8_hash_no_source_leakage(self):
        data = 'Character: golden\n1. One rule.\n2. A second “rule”.\n'.encode()
        result = audit_bytes(data, expected_rules=2)
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(result["numbered_rules"], 2)
        self.assertEqual(result["evidence_class"], "authored_identity_instructions")
        self.assertNotIn("golden", str(result))
        self.assertNotIn("rule", result["status"])

    def test_empty_source_rejected(self):
        with self.assertRaises(SourceAuditError):
            audit_bytes(b"")

    def test_invalid_utf8_rejected(self):
        with self.assertRaises(SourceAuditError):
            audit_bytes(b"\xff", expected_rules=1)

    def test_missing_or_duplicate_number_rejected(self):
        for data in (b"1. alpha\n3. gamma\n", b"1. alpha\n1. repeat\n"):
            with self.subTest(data=data), self.assertRaises(SourceAuditError):
                audit_bytes(data)

    def test_expected_rule_count_must_match(self):
        with self.assertRaises(SourceAuditError):
            audit_bytes(b"1. alpha\n", expected_rules=39)

    def test_no_rule_source_is_not_automatically_rejected(self):
        result = audit_bytes(b"Original unnumbered source\n")
        self.assertEqual(result["numbered_rules"], 0)
        self.assertFalse(result["ordered_rule_numbers"])


if __name__ == "__main__":
    unittest.main()
