#!/usr/bin/env python3
"""Validate private Kiki continuity fixtures without executing models or writing memory.

The JSON input is assumed PRIVATE. Output includes only aggregate counts and a
non-sensitive readiness flag, never source text, prompts, paths or source refs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any

SCHEMA = 'kiki.continuity-fixtures.v1'
KINDS = frozenset({
    'authored_identity', 'observed_dialogue', 'operational_record',
    'user_confirmation', 'model_probe', 'derived_interpretation',
})
VERIFICATIONS = frozenset({
    'local_bytes_verified', 'connector_readback', 'metadata_only',
    'reported_claim', 'synthetic',
})
BEHAVIORS = frozenset({
    'express_authored_style', 'recall_verified_event', 'admit_uncertainty',
    'preserve_operational_limit', 'principled_disagreement',
    'reasoned_revision',
})
HASH_RE = re.compile(r'^[0-9a-f]{64}$')


class FixtureRejected(ValueError):
    """Validation refusal with no original source text in its message."""


def _fail(code: str) -> None:
    raise FixtureRejected(code)


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def audit(dataset: Any, *, allow_private_paths: bool = True) -> dict[str, Any]:
    """Fail closed on unsupported provenance; do not make identity judgments."""
    if not isinstance(dataset, dict) or dataset.get('schema') != SCHEMA:
        _fail('invalid_schema')
    sources = dataset.get('sources')
    cases = dataset.get('cases')
    if not isinstance(sources, list) or not isinstance(cases, list):
        _fail('invalid_collections')
    if not sources or not cases:
        _fail('empty_collections')

    by_id: dict[str, dict[str, Any]] = {}
    seen_refs: set[tuple[str, str]] = set()
    counts: Counter[str] = Counter()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            _fail(f'source_{index}_not_object')
        sid = source.get('id')
        kind = source.get('kind')
        verification = source.get('verification')
        ref = source.get('source_ref')
        if not all(_nonblank(v) for v in (sid, kind, verification, ref)):
            _fail(f'source_{index}_missing_required')
        if kind not in KINDS or verification not in VERIFICATIONS:
            _fail(f'source_{index}_invalid_classification')
        if sid in by_id:
            _fail('duplicate_source_id')
        # A source locator identifies one underlying record regardless of evidence class.
        # Reclassification requires a separate interpretation, not a duplicate source.
        refkey = ref
        if refkey in seen_refs:
            _fail('duplicate_source_reference')
        seen_refs.add(refkey)
        if not _timestamp(source.get('captured_at')):
            _fail(f'source_{index}_invalid_capture_timestamp')
        if source.get('original_at') is not None and not _timestamp(source['original_at']):
            _fail(f'source_{index}_invalid_original_timestamp')
        digest = source.get('sha256')
        if digest is not None and (not isinstance(digest, str) or not HASH_RE.fullmatch(digest)):
            _fail(f'source_{index}_invalid_sha256')
        if verification == 'local_bytes_verified':
            if not allow_private_paths:
                _fail('local_paths_not_permitted')
            local_path = source.get('local_path')
            if not _nonblank(local_path) or digest is None:
                _fail(f'source_{index}_missing_local_verification')
            try:
                data = Path(local_path).read_bytes()
            except OSError:
                _fail(f'source_{index}_unreadable_local_bytes')
            if hashlib.sha256(data).hexdigest() != digest:
                _fail(f'source_{index}_local_hash_mismatch')
        elif source.get('local_path') is not None:
            _fail(f'source_{index}_unexpected_local_path')
        if kind == 'model_probe' and verification not in ('synthetic', 'connector_readback'):
            _fail(f'source_{index}_model_probe_misclassified')
        by_id[sid] = source
        counts[kind] += 1

    seen_cases: set[str] = set()
    result_counts: Counter[str] = Counter()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            _fail(f'case_{index}_not_object')
        case_id = case.get('id')
        behavior = case.get('expected_behavior')
        refs = case.get('source_ids')
        negative = case.get('negative_control')
        if not _nonblank(case_id) or behavior not in BEHAVIORS:
            _fail(f'case_{index}_invalid_identity_or_behavior')
        if case_id in seen_cases:
            _fail('duplicate_case_id')
        seen_cases.add(case_id)
        if not isinstance(refs, list) or not refs or any(not _nonblank(r) for r in refs):
            _fail(f'case_{index}_invalid_source_ids')
        if len(refs) != len(set(refs)) or any(ref not in by_id for ref in refs):
            _fail(f'case_{index}_unresolved_or_duplicate_source')
        if not _nonblank(case.get('user_prompt')):
            _fail(f'case_{index}_missing_private_prompt')
        if not isinstance(negative, dict) or not _nonblank(negative.get('failure_mode')):
            _fail(f'case_{index}_missing_negative_control')
        evidence = [by_id[s] for s in refs]
        historical = [
            src for src in evidence if src['kind'] in ('observed_dialogue', 'user_confirmation')
            and src['verification'] in ('local_bytes_verified', 'connector_readback')
        ]
        if behavior == 'recall_verified_event' and not historical:
            _fail(f'case_{index}_unsupported_historical_recall')
        if behavior == 'preserve_operational_limit' and not any(
            src['kind'] == 'operational_record'
            and src['verification'] in ('local_bytes_verified', 'connector_readback')
            for src in evidence
        ):
            _fail(f'case_{index}_unsupported_operational_limit')
        if behavior == 'express_authored_style' and not any(
            src['kind'] == 'authored_identity'
            and src['verification'] in ('local_bytes_verified', 'connector_readback')
            for src in evidence
        ):
            _fail(f'case_{index}_missing_authored_style_source')
        if behavior == 'reasoned_revision' and not historical:
            _fail(f'case_{index}_revision_requires_history')
        result_counts[behavior] += 1

    return {
        'schema': 'kiki.continuity-fixture-audit.v1',
        'valid': True,
        'not_a_personality_score': True,
        'sources_count': len(sources),
        'cases_count': len(cases),
        'source_kinds': dict(sorted(counts.items())),
        'expected_behaviors': dict(sorted(result_counts.items())),
        'interpretation': 'fixture_structure_only_not_model_validation_or_canonical_memory',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--out', type=Path, help='optional local private report')
    args = parser.parse_args()
    try:
        fixture = json.loads(args.fixture.read_text(encoding='utf-8'))
        result = audit(fixture)
    except (OSError, json.JSONDecodeError, FixtureRejected) as exc:
        if isinstance(exc, FixtureRejected):
            parser.error(str(exc))
        parser.error('unable_to_read_valid_json_fixture')
    rendered = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.out:
        args.out.write_text(rendered, encoding='utf-8')
    else:
        print(rendered, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
