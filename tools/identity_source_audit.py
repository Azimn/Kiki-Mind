#!/usr/bin/env python3
"""Audit an authored identity source without publishing or interpreting its contents.

This utility does not import into canonical memory, claim observed behavior, or
send source text anywhere. Its output is a bounded, private-source fingerprint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

_RULE = re.compile(r"^[ \t]*(\d+)\.[ \t]+(.+)$", re.MULTILINE)


class SourceAuditError(ValueError):
    """The source could not be audited without losing provenance."""


def audit_bytes(data: bytes, *, expected_rules: int | None = None) -> dict:
    if not data:
        raise SourceAuditError("source is empty")
    try:
        content = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceAuditError("source is not valid UTF-8") from exc
    hits = [(int(number), body) for number, body in _RULE.findall(content)]
    numbers = [number for number, _ in hits]
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        raise SourceAuditError("numbered rules are missing, duplicated, or out of order")
    if expected_rules is not None and len(hits) != expected_rules:
        raise SourceAuditError(
            f"expected {expected_rules} ordered numbered rules; found {len(hits)}"
        )
    return {
        "schema": "kiki.authored-source-audit.v1",
        "evidence_class": "authored_identity_instructions",
        "status": "source_fingerprint_only_not_behavior_or_memory",
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "utf8": True,
        "numbered_rules": len(hits),
        "ordered_rule_numbers": bool(hits),
        "ends_with_newline": data.endswith(b"\n"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="local source file, never uploaded")
    parser.add_argument("--expect-rules", type=int, default=None)
    parser.add_argument("--out", type=Path, default=None, help="optional local manifest")
    args = parser.parse_args(argv)
    if args.expect_rules is not None and args.expect_rules < 1:
        parser.error("--expect-rules must be positive")
    try:
        result = audit_bytes(args.source.read_bytes(), expected_rules=args.expect_rules)
    except (OSError, SourceAuditError) as exc:
        parser.error(str(exc))
    output = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
