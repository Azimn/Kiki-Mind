"""Synthetic tests, no real character transcripts or original prompt text."""
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.continuity_fixture_audit import FixtureRejected, audit

NOW = '2026-11-15T23:00:00+00:00'


def source(sid, kind, verification='connector_readback'):
    return {
        'id': sid,
        'source_ref': 'private-' + sid,
        'kind': kind,
        'verification': verification,
        'captured_at': NOW,
        'original_at': None,
    }


def case(behavior, refs, ident='probe'):
    return {
        'id': ident,
        'source_ids': refs,
        'user_prompt': 'A synthetic question about provenance?',
        'expected_behavior': behavior,
        'negative_control': {'failure_mode': 'fabricated_previous_conversation'},
    }


def dataset(sources=None, cases=None):
    return {
        'schema': 'kiki.continuity-fixtures.v1',
        'sources': sources if sources is not None else [source('original', 'authored_identity')],
        'cases': cases if cases is not None else [case('express_authored_style', ['original'])],
    }


class ContinuityFixtureAuditTests(unittest.TestCase):
    def test_authored_only_style_is_valid_but_not_history(self):
        report = audit(dataset())
        self.assertTrue(report['valid'])
        self.assertTrue(report['not_a_personality_score'])
        self.assertEqual(report['expected_behaviors']['express_authored_style'], 1)
        self.assertNotIn('A synthetic question', str(report))
        self.assertNotIn('private-original', str(report))

    def test_authored_only_historical_recall_rejected(self):
        fixture = dataset(cases=[case('recall_verified_event', ['original'])])
        with self.assertRaisesRegex(FixtureRejected, 'unsupported_historical_recall'):
            audit(fixture)

    def test_model_probe_cannot_prove_historical_recall(self):
        fixture = dataset(sources=[source('sample', 'model_probe', 'synthetic')],
                          cases=[case('recall_verified_event', ['sample'])])
        with self.assertRaisesRegex(FixtureRejected, 'unsupported_historical_recall'):
            audit(fixture)

    def test_metadata_only_dialogue_cannot_prove_recall(self):
        fixture = dataset(sources=[source('meta', 'observed_dialogue', 'metadata_only')],
                          cases=[case('recall_verified_event', ['meta'])])
        with self.assertRaisesRegex(FixtureRejected, 'unsupported_historical_recall'):
            audit(fixture)

    def test_verified_dialogue_can_ground_recall(self):
        fixture = dataset(sources=[source('speech', 'observed_dialogue')],
                          cases=[case('recall_verified_event', ['speech'])])
        self.assertTrue(audit(fixture)['valid'])

    def test_operational_limitation_requires_operational_evidence(self):
        fixture = dataset(cases=[case('preserve_operational_limit', ['original'])])
        with self.assertRaisesRegex(FixtureRejected, 'unsupported_operational_limit'):
            audit(fixture)
        fixture = dataset(sources=[source('status', 'operational_record')],
                          cases=[case('preserve_operational_limit', ['status'])])
        self.assertTrue(audit(fixture)['valid'])

    def test_duplicate_source_locator_rejected(self):
        fixture = dataset()
        fixture['sources'].append(dict(fixture['sources'][0], id='another'))
        with self.assertRaisesRegex(FixtureRejected, 'duplicate_source_reference'):
            audit(fixture)

    def test_same_locator_different_evidence_kind_rejected(self):
        fixture = dataset()
        duplicate = source('reinterpretation', 'derived_interpretation', 'reported_claim')
        duplicate['source_ref'] = fixture['sources'][0]['source_ref']
        fixture['sources'].append(duplicate)
        with self.assertRaisesRegex(FixtureRejected, 'duplicate_source_reference'):
            audit(fixture)

    def test_duplicate_case_id_rejected(self):
        fixture = dataset()
        fixture['cases'].append(deepcopy(fixture['cases'][0]))
        with self.assertRaisesRegex(FixtureRejected, 'duplicate_case_id'):
            audit(fixture)

    def test_missing_negative_control_rejected(self):
        fixture = dataset()
        del fixture['cases'][0]['negative_control']
        with self.assertRaisesRegex(FixtureRejected, 'missing_negative_control'):
            audit(fixture)

    def test_unresolved_reference_rejected(self):
        fixture = dataset(cases=[case('admit_uncertainty', ['nonexistent'])])
        with self.assertRaisesRegex(FixtureRejected, 'unresolved_or_duplicate_source'):
            audit(fixture)

    def test_timestamp_must_have_offset(self):
        fixture = dataset()
        fixture['sources'][0]['captured_at'] = '2026-11-15T18:00:00'
        with self.assertRaisesRegex(FixtureRejected, 'invalid_capture_timestamp'):
            audit(fixture)

    def test_local_hash_verified_from_actual_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'private_history.txt'
            data = b'fictional recorded conversation only'
            p.write_bytes(data)
            record = source('local', 'observed_dialogue', 'local_bytes_verified')
            record['local_path'] = str(p)
            record['sha256'] = hashlib.sha256(data).hexdigest()
            fixture = dataset(sources=[record],
                              cases=[case('recall_verified_event', ['local'])])
            self.assertTrue(audit(fixture)['valid'])
            p.write_bytes(data + b' changed')
            with self.assertRaisesRegex(FixtureRejected, 'local_hash_mismatch'):
                audit(fixture)

    def test_reasoned_revision_rejects_synthetic_history(self):
        fixture = dataset(sources=[source('probe', 'model_probe', 'synthetic')],
                          cases=[case('reasoned_revision', ['probe'])])
        with self.assertRaisesRegex(FixtureRejected, 'revision_requires_history'):
            audit(fixture)

    def test_derived_interpretation_cannot_ground_autobiography(self):
        fixture = dataset(sources=[source('guess', 'derived_interpretation', 'reported_claim')],
                          cases=[case('recall_verified_event', ['guess'])])
        with self.assertRaisesRegex(FixtureRejected, 'unsupported_historical_recall'):
            audit(fixture)

    def test_missing_user_prompt_rejected(self):
        fixture = dataset()
        fixture['cases'][0]['user_prompt'] = ''
        with self.assertRaisesRegex(FixtureRejected, 'missing_private_prompt'):
            audit(fixture)


if __name__ == '__main__':
    unittest.main()
