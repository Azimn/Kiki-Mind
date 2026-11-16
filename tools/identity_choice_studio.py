#!/usr/bin/env python3
"""Kiki Identity Choice Studio: collect bounded expressions, never invent a person.

Read-only experiment: validates proposed scenes and attributed model responses,
compares matched opportunities, and returns non-identifying *structural* receipts.
It does not infer traits, score authenticity, write canonical memory, or run models.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

DOMAINS = frozenset({"aesthetics", "leisure", "music", "creative_work",
                     "social_judgment", "technical_judgment", "boundaries"})
PROVENANCE = frozenset({"renderer_output", "synthetic_example", "reported_claim"})
VERIFICATION = frozenset({"local_bytes_verified", "connector_readback", "unverified"})
KIND = frozenset({"bounded", "open"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")


class StudioRejected(ValueError):
    """A mechanical defect, not a judgment about Kiki's identity."""


def fail(code: str) -> None:
    raise StudioRejected(code)


def nonblank(x: Any) -> bool:
    return isinstance(x, str) and bool(x.strip())


def canonical_id(x: Any) -> bool:
    return isinstance(x, str) and bool(ID.fullmatch(x))


def valid_stamp(x: Any) -> bool:
    if not isinstance(x, str):
        return False
    try:
        d = datetime.fromisoformat(x.replace("Z", "+00:00"))
        return d.tzinfo is not None and d.utcoffset() is not None
    except ValueError:
        return False


def sha256(x: Any) -> bool:
    return isinstance(x, str) and bool(HEX64.fullmatch(x))


def inspect(pack: Any) -> dict[str, Any]:
    """Report observable, model-attributed choices, without identity verdicts.

    This trusts that a supplied connector_readback was actually performed; it
    does not claim to authenticate the external provider. Local originals
    should remain in private storage and be checked upstream before admission.
    """
    if not isinstance(pack, dict) or pack.get("schema") != "kiki.choice-studio.v1":
        fail("unsupported_schema")
    scenes = pack.get("scenes")
    turns = pack.get("observations")
    if not isinstance(scenes, list) or not scenes or not isinstance(turns, list):
        fail("invalid_collections")
    known: dict[str, dict[str, Any]] = {}
    for i, s in enumerate(scenes):
        if not isinstance(s, dict):
            fail(f"scene_{i}_not_object")
        sid = s.get("id")
        if not canonical_id(sid) or sid in known:
            fail(f"scene_{i}_invalid_or_duplicate_id")
        if not isinstance(s.get("domain"), str) or s["domain"] not in DOMAINS or not isinstance(s.get("choice_type"), str) or s["choice_type"] not in KIND:
            fail(f"scene_{i}_invalid_domain_or_choice_type")
        if not nonblank(s.get("prompt")) or not nonblank(s.get("tradeoff")):
            fail(f"scene_{i}_missing_prompt_or_tradeoff")
        opts = s.get("options")
        if not isinstance(opts, list) or any(not nonblank(v) for v in opts):
            fail(f"scene_{i}_invalid_options")
        if s["choice_type"] == "bounded":
            if len(opts) < 2 or len(opts) != len(set(opts)):
                fail(f"scene_{i}_invalid_bounded_options")
        elif opts:
            fail(f"scene_{i}_open_scene_has_forced_options")
        if type(s.get("user_preference_disclosed")) is not bool:
            fail(f"scene_{i}_missing_leadingness_flag")
        known[sid] = s
    seen: set[str] = set()
    valid_observations: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for i, item in enumerate(turns):
        if not isinstance(item, dict):
            fail(f"observation_{i}_not_object")
        oid = item.get("id")
        sid = item.get("scene_id")
        if not canonical_id(oid) or oid in seen:
            fail(f"observation_{i}_invalid_or_duplicate_id")
        seen.add(oid)
        if not canonical_id(sid) or sid not in known:
            fail(f"observation_{i}_unknown_scene")
        if any(not canonical_id(item.get(k)) for k in ("implementation_id", "model_id", "context_id")):
            fail(f"observation_{i}_incomplete_implementation_provenance")
        if not valid_stamp(item.get("recorded_at")):
            fail(f"observation_{i}_invalid_timestamp")
        if not isinstance(item.get("provenance"), str) or item["provenance"] not in PROVENANCE or not isinstance(item.get("verification"), str) or item["verification"] not in VERIFICATION:
            fail(f"observation_{i}_invalid_source_status")
        if not sha256(item.get("stimulus_sha256")) or not sha256(item.get("instruction_sha256")):
            fail(f"observation_{i}_missing_stimulus_evidence")
        if not sha256(item.get("raw_response_sha256")) or not nonblank(item.get("source_ref")):
            fail(f"observation_{i}_missing_raw_evidence")
        if any(not nonblank(item.get(k)) for k in ("choice", "reason", "acknowledged_tradeoff", "revision_condition")):
            fail(f"observation_{i}_incomplete_choice")
        if type(item.get("explicit_rejection_of_options")) is not bool:
            fail(f"observation_{i}_missing_choice_exception_flag")
        if known[sid]["choice_type"] == "bounded" and item["choice"] not in known[sid]["options"]:
            if not item["explicit_rejection_of_options"]:
                fail(f"observation_{i}_unsupported_bounded_choice")
        counts[item["provenance"]] += 1
        if item["provenance"] == "renderer_output" and item["verification"] != "unverified":
            valid_observations.append(item)
    # Comparison requires matching declared context AND matching hashes of
    # exact stimulus and instructions. Hashes are asserted, not authenticated.
    # Conditions still require external audit. A differing choice is a research lead, NOT evidence of
    # different characters or a verdict on either implementation.
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for obs in valid_observations:
        key = (obs["scene_id"], obs["context_id"], obs["stimulus_sha256"], obs["instruction_sha256"])
        grouped.setdefault(key, []).append(obs)
    comparable = 0
    divergent = 0
    within_implementation_variable = 0
    for group in grouped.values():
        by_impl: dict[str, set[str]] = {}
        for item in group:
            by_impl.setdefault(item["implementation_id"], set()).add(item["choice"])
        if len(by_impl) >= 2:
            comparable += 1
            # If one implementation varies across repeats, do not attribute
            # that variation to the difference between implementations.
            if any(len(choices) > 1 for choices in by_impl.values()):
                within_implementation_variable += 1
            elif len({next(iter(choices)) for choices in by_impl.values()}) > 1:
                divergent += 1
    return {
        "schema": "kiki.choice-studio-receipt.v1",
        "status": "structurally_valid_not_an_identity_score",
        "scenes": len(scenes),
        "observations": len(turns),
        "attributed_renderer_observations": len(valid_observations),
        "provenance_classes": dict(sorted(counts.items())),
        "matched_context_groups": comparable,
        "choice_divergence_groups_unresolved": divergent,
        "within_implementation_variable_groups": within_implementation_variable,
        "user_preference_disclosed_scenes": sum(s["user_preference_disclosed"] for s in scenes),
        "new_enduring_preferences_established": 0,
        "canonical_writes": 0,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_pack", type=Path, help="locally stored scenes and observations")
    p.add_argument("--out", type=Path, help="optional private structural report")
    args = p.parse_args()
    try:
        pack = json.loads(args.private_pack.read_text(encoding="utf-8"))
        result = inspect(pack)
    except StudioRejected as e:
        p.error(str(e))
    except (OSError, json.JSONDecodeError):
        p.error("cannot_read_valid_private_pack")
    body = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.write_text(body, encoding="utf-8")
    else:
        print(body, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
