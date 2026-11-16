#!/usr/bin/env python3
"""Locally verify exact private Kiki Choice Studio evidence bytes.

Manifest paths are relative to a private evidence root. Never publish a
populated manifest or private original evidence. No network or canonical writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

HEX64 = re.compile(r"^[0-9a-f]{64}$")
FIELDS = ("stimulus", "instruction", "response")


class EvidenceRejected(ValueError):
    pass


def _reject(reason: str) -> None:
    raise EvidenceRejected(reason)


def _safe_file(root: Path, rel: object) -> Path:
    if not isinstance(rel, str) or not rel or "\\" in rel:
        _reject("invalid_relative_path")
    path = PurePosixPath(rel)
    if path.is_absolute() or any(p in ("", ".", "..") for p in rel.split("/")):
        _reject("invalid_relative_path")
    base = root.resolve(strict=True)
    candidate = (base / rel).resolve(strict=True)
    if not candidate.is_relative_to(base) or not candidate.is_file():
        _reject("evidence_path_outside_root_or_not_file")
    return candidate


def verify(manifest: object, root: Path) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema") != "kiki.choice-evidence.v1":
        _reject("unsupported_manifest")
    items = manifest.get("observations")
    if not isinstance(items, list) or not items:
        _reject("missing_observations")
    ids: set[str] = set()
    verified = 0
    for item in items:
        if not isinstance(item, dict):
            _reject("invalid_observation")
        oid = item.get("id")
        if not isinstance(oid, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", oid) or oid in ids:
            _reject("invalid_or_duplicate_observation_id")
        ids.add(oid)
        for field in FIELDS:
            entry = item.get(field)
            if not isinstance(entry, dict):
                _reject("missing_evidence_field")
            expected = entry.get("sha256")
            if not isinstance(expected, str) or not HEX64.fullmatch(expected):
                _reject("invalid_expected_hash")
            file = _safe_file(root, entry.get("path"))
            actual = hashlib.sha256(file.read_bytes()).hexdigest()
            if actual != expected:
                _reject("evidence_hash_mismatch")
            verified += 1
    return {
        "schema": "kiki.choice-evidence-receipt.v1",
        "status": "local_evidence_bytes_verified_not_provider_authenticated",
        "observations": len(items),
        "verified_files": verified,
        "canonical_writes": 0,
        "enduring_preferences_established": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_manifest", type=Path)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.private_manifest.read_text(encoding="utf-8"))
        result = verify(manifest, args.private_root)
    except (OSError, json.JSONDecodeError, EvidenceRejected) as error:
        parser.error("verification_failed: " + type(error).__name__)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
