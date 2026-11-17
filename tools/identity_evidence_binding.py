#!/usr/bin/env python3
"""Audit exact local bytes and bind each observation to its evidence manifest.

This is not provider authentication, model execution, or a canonical memory write.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.identity_choice_studio import inspect, StudioRejected
from tools.identity_evidence_manifest import verify, EvidenceRejected

MAP = {"stimulus": "stimulus_sha256",
       "instruction": "instruction_sha256",
       "response": "raw_response_sha256"}


class BindingRejected(ValueError):
    pass


def bind(pack: object, manifest: object, root: Path) -> dict:
    """Fail closed on any unpaired, mismatched or non-local observation."""
    if not isinstance(pack, dict) or not isinstance(manifest, dict):
        raise BindingRejected("invalid_packet")
    try:
        inspect(pack)
        verified = verify(manifest, root)
    except (StudioRejected, EvidenceRejected, OSError) as exc:
        raise BindingRejected("upstream_validation_failed") from exc
    observations = pack["observations"]
    evidence = manifest["observations"]
    if len(observations) != len(evidence):
        raise BindingRejected("observation_count_mismatch")
    by_id = {item["id"]: item for item in evidence}
    if {item["id"] for item in observations} != set(by_id):
        raise BindingRejected("observation_id_mismatch")
    for obs in observations:
        entry = by_id[obs["id"]]
        for field, key in MAP.items():
            if obs[key] != entry[field]["sha256"]:
                raise BindingRejected("observation_hash_mismatch")
        if obs["verification"] != "local_bytes_verified":
            raise BindingRejected("unverified_observation_claim")
    summary = inspect(pack)
    # No individual response, prompt, private path, source ref or model ID.
    return {
        "schema": "kiki.choice-bound-evidence-receipt.v1",
        "status": "local_bytes_bound_not_provider_authenticated",
        "bound_observations": len(observations),
        "verified_files": verified["verified_files"],
        "matched_context_groups": summary["matched_context_groups"],
        "choice_divergence_groups_unresolved": summary["choice_divergence_groups_unresolved"],
        "new_enduring_preferences_established": 0,
        "canonical_writes": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_pack", type=Path)
    parser.add_argument("private_manifest", type=Path)
    parser.add_argument("private_root", type=Path)
    args = parser.parse_args()
    try:
        pack = json.loads(args.private_pack.read_text(encoding="utf-8"))
        manifest = json.loads(args.private_manifest.read_text(encoding="utf-8"))
        receipt = bind(pack, manifest, args.private_root)
    except (BindingRejected, OSError, ValueError, TypeError):
        parser.error("private_evidence_binding_failed")
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
