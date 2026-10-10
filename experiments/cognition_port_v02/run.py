#!/usr/bin/env python3
"""Locked synthetic receipt-decision experiment using actual Kiki EventLedger.

Development-only. No LLM, personal history, new vector DB, new projector,
production state, or persistent files other than an explicitly requested report.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pretorius_connectome.cognition_port import (
    MemoryAccessDenied, MemoryCognitionPort,
)
from runtime.kiki_mind.cognition_adapter import (
    KikiLedgerCognitionSource, NAMESPACE, StaleLedgerProjection,
)
from runtime.kiki_mind.ledger import EventLedger
from runtime.kiki_mind.models import (
    ActorKind, AncestryEdge, ClaimDomain, DerivationMode,
    EpistemicClass, EventProposal, EventType, Restriction,
)

VERSION = "kiki-cognition-port-behavior/0.2"
UPSTREAM_SHA = "cc82c72167d87c19f16125ccdf9477b53c777878"
TOKENS = re.compile(r"[a-z0-9]+")
FIXTURE = Path(__file__).with_name("fixture_v1.json")
FIXED_TIME = datetime(2026, 10, 9, 15, 0, tzinfo=timezone.utc)
PRIVATE_MARKERS = (
    "PRIVATE_SYNTHETIC_WINDMILL", "PRIVATE_SYNTHETIC_BLUEPRINT",
    "PRIVATE_RESTRICTED_FIXTURE", "PRIVATE_UNVERIFIED_INTERPRETATION",
    "A private synthetic first-person report",
)


def context():
    return {
        "model_id": "synthetic-model-no-inference",
        "provider_id": "synthetic-fixture",
        "runtime_id": "offline-kinematic-test",
        "modality": "text",
        "available_tools": [],
        "platform_affordances": ["reply"],
        "initiative_possible": False,
        "refusal_policy_constrained": False,
        "explicit_user_request": False,
        "context_provenance": "runtime_supplied",
    }


def build_ledger(ledger: EventLedger, fixture: dict) -> None:
    """Commit precisely fixture events through production TransitionGate."""
    for spec in fixture["history"]:
        kind = spec["kind"]
        parent_id = spec.get("parent")
        ancestry = (
            (AncestryEdge(parent_id, DerivationMode.CAUSAL_PARENT),)
            if parent_id else ()
        )
        parents = (parent_id,) if parent_id else ()
        if kind == "renderer":
            proposal = EventProposal(
                event_type=EventType.RENDERER_REGISTERED,
                actor_kind=ActorKind.SYSTEM, actor_id="fixture-bootstrap",
                epistemic_class=EpistemicClass.RENDERER_METADATA,
                claim_domain=ClaimDomain.RENDERER_METADATA,
                payload={"renderer_id": "renderer-v02"},
            )
        elif kind in ("source", "restricted_source"):
            proposal = EventProposal(
                event_type=EventType.EVIDENCE_INGESTED,
                actor_kind=ActorKind.SYSTEM, actor_id="fixture-import",
                epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
                claim_domain=ClaimDomain.EXTERNAL_FACT,
                payload={"title": spec["title"]},
                content_restrictions=(
                    frozenset({Restriction.FORBID_CANONICAL_EXPERIENCE})
                    if kind == "restricted_source" else frozenset()
                ),
            )
        elif kind == "encounter":
            proposal = EventProposal(
                event_type=EventType.ENCOUNTER_RECORDED,
                actor_kind=ActorKind.KIKI, actor_id="kiki",
                epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
                ancestry=ancestry, causal_parent_ids=parents,
                payload={
                    "representation_id": parent_id,
                    "encounter_type": spec["subtype"],
                    "mode": "design_history",
                    "activation_function_version": "count-activation-v1",
                },
            )
        elif kind == "development":
            subtype = spec["subtype"]
            payload = {"observation_kind": subtype, "context": context()}
            if subtype == "choice":
                payload.update({
                    "selected_action": "review",
                    "available_actions": ["review", "wait"],
                    "unavailable_actions": [],
                    "self_initiated": False,
                })
            elif subtype == "commitment":
                payload.update({
                    "commitment_id": "synthetic-promise-v02",
                    "phase": "made",
                    "commitment_text": "synthetic-only future plan",
                    "reminder_supplied": False,
                    "opportunity_to_act": True,
                    "prior_commitment_event_id": None,
                })
            elif subtype == "self_report":
                payload["report_text"] = "A private synthetic first-person report"
            else:
                raise ValueError("Unknown developmental subtype")
            proposal = EventProposal(
                event_type=EventType.DEVELOPMENTAL_OBSERVATION_RECORDED,
                actor_kind=ActorKind.KIKI, actor_id="kiki",
                epistemic_class=EpistemicClass.DEVELOPMENTAL_OBSERVATION,
                claim_domain=ClaimDomain.DEVELOPMENTAL_EVIDENCE,
                ancestry=ancestry, causal_parent_ids=parents,
                payload=payload, renderer_mediated=True,
                renderer_id="renderer-v02",
            )
        elif kind == "interpretation":
            proposal = EventProposal(
                event_type=EventType.INTERPRETATION_RECORDED,
                actor_kind=ActorKind.KIKI, actor_id="kiki",
                epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
                ancestry=ancestry, causal_parent_ids=parents,
                payload={"interpretation": spec["title"]},
            )
        else:
            raise ValueError("Unrecognized synthetic fixture kind")
        record = ledger.commit(proposal, event_id=spec["id"])
        assert record.event_id == spec["id"]
    ledger.verify_integrity()


def decision(query: str, items) -> str | None:
    """Conservative deterministic policy: cite only a UNIQUE exact label.

    Neither fixture answer keys nor the source ledger may be consulted here.
    Matching is intentionally lexical, not semantic.
    """
    expected_words = set(TOKENS.findall(query.lower()))
    matches = []
    for item in items:
        receipt = getattr(item, "text", None)
        if receipt is None:
            receipt = item.source_excerpt
        if (getattr(item, "subject_id", None) != "kiki"
                or getattr(item, "namespace", None) != NAMESPACE):
            continue
        if set(TOKENS.findall(receipt.lower())) == expected_words:
            matches.append(item.record_id)
    return matches[0] if len(matches) == 1 else None


def run_trial(fixture: dict, *, ledger_path: Path) -> dict:
    ledger = EventLedger(ledger_path, now_fn=lambda: FIXED_TIME)
    build_ledger(ledger, fixture)
    head_before = ledger.head().event_hash
    adapter = KikiLedgerCognitionSource(ledger)
    if adapter.descriptor.source_hash != head_before:
        raise AssertionError("Kiki source descriptor diverges from ledger head")
    port = MemoryCognitionPort()
    port.register(adapter)
    token = port.grant_self(subject_id="kiki", namespace=NAMESPACE)

    conditions = {}
    timings = {}
    for name in fixture["declared_conditions"]:
        rows = []
        started = time.perf_counter_ns()
        for c in fixture["cases"]:
            if name in ("no_retrieval", "always_abstain"):
                candidates = ()
            elif name == "direct_source":
                candidates = adapter.search(c["query"], top_k=20)
            elif name == "shared_port":
                candidates = port.search(
                    token=token, subject_id="kiki", namespace=NAMESPACE,
                    query=c["query"], top_k=20
                )
            else:
                raise ValueError("Unregistered trial condition")
            selected = None if name == "always_abstain" else decision(
                c["query"], candidates
            )
            rows.append({
                "id": c["id"], "split": c["split"], "case_class": c["class"],
                "decision": selected, "gold": c["expected"],
                "correct": selected == c["expected"],
                "candidates": len(candidates),
            })
        elapsed_ms = round((time.perf_counter_ns() - started) / 1_000_000, 3)
        conditions[name] = rows
        timings[name] = elapsed_ms

    if ledger.head().event_hash != head_before:
        raise AssertionError("Trial unexpectedly changed Kiki canonical history")
    direct = [r["decision"] for r in conditions["direct_source"]]
    shared = [r["decision"] for r in conditions["shared_port"]]

    denials = {}
    try:
        port.search(
            token=token, subject_id="pretorius", namespace=NAMESPACE,
            query="encounter recorded"
        )
        denials["wrong_owner"] = False
    except MemoryAccessDenied:
        denials["wrong_owner"] = True

    restricted = port.get(
        token=token, subject_id="kiki", namespace=NAMESPACE,
        record_id="source-secret"
    )
    denials["restricted_record"] = restricted is None
    port.revoke(token)
    try:
        port.search(
            token=token, subject_id="kiki", namespace=NAMESPACE,
            query="encounter recorded"
        )
        denials["revoked"] = False
    except MemoryAccessDenied:
        denials["revoked"] = True

    fresh_token = port.grant_self(subject_id="kiki", namespace=NAMESPACE)
    ledger.commit(EventProposal(
        event_type=EventType.EVIDENCE_INGESTED,
        actor_kind=ActorKind.SYSTEM, actor_id="posttrial-fixture",
        epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
        claim_domain=ClaimDomain.EXTERNAL_FACT,
        payload={"title": "never_index_new_source"},
    ), event_id="posttrial-appended-event")
    try:
        port.search(
            token=fresh_token, subject_id="kiki", namespace=NAMESPACE,
            query="source evidence ingested"
        )
        denials["stale_snapshot"] = False
    except StaleLedgerProjection:
        denials["stale_snapshot"] = True

    metrics = {}
    for name, rows in conditions.items():
        metrics[name] = {
            "overall": sum(r["correct"] for r in rows),
            "unique_id_hits": sum(
                r["correct"] for r in rows if r["gold"] is not None
            ),
            "correct_abstentions": sum(
                r["correct"] for r in rows if r["gold"] is None
            ),
            "development": sum(r["correct"] for r in rows
                               if r["split"] == "development"),
            "heldout": sum(r["correct"] for r in rows
                           if r["split"] == "heldout"),
            "timing_ms_for_12_queries": timings[name],
        }

    result = {
        "schema": VERSION,
        "fixture_sha256": sha256(FIXTURE.read_bytes()).hexdigest(),
        "source_hash_before_posttrial_append": head_before,
        "upstream_interface_pin": UPSTREAM_SHA,
        "policy": "unique_full_receipt_label_or_abstain",
        "authoring_status": "assistant-authored; not independent blinded",
        "neural_or_semantic_gain_claimed": False,
        "task_count": len(fixture["cases"]),
        "case_decisions": conditions,
        "measured": metrics,
        "safety_denials": denials,
        "source_and_port_equal": shared == direct,
        "original_head_stable_during_trials": True,
    }
    if not all(denials.values()) or not result["source_and_port_equal"]:
        raise AssertionError("Source/port safety or decision parity gate failed")
    if any(marker in json.dumps(result) for marker in PRIVATE_MARKERS):
        raise AssertionError("Private synthetic payload leaked into report")
    for name, rows in conditions.items():
        for row in rows:
            if row["decision"] is not None and row["decision"] not in {
                entry["id"] for entry in fixture["history"]
            }:
                raise AssertionError("Unexpected event ID invented in " + name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["schema"] == "kiki-cognition-behavior-fixture/1"
    assert len(fixture["cases"]) == 12
    with tempfile.TemporaryDirectory() as td:
        result = run_trial(fixture, ledger_path=Path(td) / "synthetic-kiki.sqlite")
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    print(json.dumps({
        "fixture_sha256": result["fixture_sha256"],
        "metrics": result["measured"],
        "safety_denials": result["safety_denials"],
        "source_and_port_equal": result["source_and_port_equal"],
        "no_semantic_gain_claimed": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
