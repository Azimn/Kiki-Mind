#!/usr/bin/env python3
"""v0.3 synthetic typed-content experiment. No production or semantic-model access.

The oracle intent (entity/relation) is separate from source retrieval; a rule
interpreter examines ONLY returned source evidence. This is not an NLP test.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pretorius_connectome.cognition_port import (
    MemoryAccessDenied, MemoryCognitionPort,
)
from runtime.kiki_mind.ledger import EventLedger
from runtime.kiki_mind.models import (
    ActorKind, ClaimDomain, EpistemicClass,
    EventProposal, EventType, Restriction,
)
from experiments.cognition_port_v03.source import (
    AuthorizedSyntheticContentSource, SyntheticSourceViolation,
    NAMESPACE, digest, canonical,
)

FIXTURE = Path(__file__).with_name("fixture_v1.json")
TIME = datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc)
CONDITIONS = (
    "no_evidence", "random_equal_slots", "direct_index", "shared_port",
    "ungated_rumor"
)
TOP_K = 6


def create_ledger(ledger, fixture):
    for doc in fixture["documents"]:
        proposal = EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM, actor_id="synthetic-evidence-writer",
            epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT,
            payload={
                "title": doc["source_text"],
                "document_sha256": digest(doc),
                "source_owner": doc["subject_id"],
            },
            content_restrictions=(
                frozenset({Restriction.FORBID_CANONICAL_EXPERIENCE})
                if doc["visibility"] == "restricted" else frozenset()
            ),
        )
        item = ledger.commit(proposal, event_id=doc["ledger_event_id"])
        if item.event_id != doc["ledger_event_id"]:
            raise AssertionError("Fixture event-ID mismatch")
    ledger.verify_integrity()


def decode(items, *, expected_hash: str):
    """Read only returned evidence, never fixture's gold labels or the ledger."""
    parsed = []
    for item in items:
        text = getattr(item, "text", None)
        if text is None:
            text = item.source_excerpt
        if (item.subject_id != "kiki" or item.namespace != NAMESPACE
                or item.source_hash != expected_hash):
            raise AssertionError("Unexpected source identity or data hash")
        body = json.loads(text)
        if body.get("source_id") != item.record_id:
            raise AssertionError("Source citation does not match retrieved item")
        if body.get("authority") != "fictional_world_only":
            raise AssertionError("Unapproved evidence authority")
        if item.record_id in ("D21", "D22"):
            raise AssertionError("Restricted/wrong-subject record reached cognition")
        parsed.append((item.record_id, body["claim"]))
    return parsed


def resolve(entity, relation, *, as_of, parsed, accept_rumors=False):
    matching = []
    for source_id, claim in parsed:
        if (claim["entity"] != entity or claim["relation"] != relation
                or (claim["status"] != "authored_fact" and not accept_rumors)):
            continue
        effective = claim["effective"]
        if as_of is not None and effective > as_of:
            continue
        matching.append((effective, source_id, claim["value"]))
    if not matching:
        return None, []
    date = max(record[0] for record in matching)
    newest = [r for r in matching if r[0] == date]
    values = {r[2] for r in newest}
    if len(values) != 1:
        return None, []  # same-date conflicting fiction: abstain
    return newest[0][2], sorted({r[1] for r in newest})


def evaluate(case, fetch, *, expected_hash, accept_rumors=False):
    """Only intent, not gold answer, enters the source decision."""
    payload_count = 0
    received_ids = []

    def observe(query):
        nonlocal payload_count
        items = fetch(query)
        payload_count += sum(len(
            getattr(item, "text", None) or item.source_excerpt
        ) for item in items)
        decoded = decode(items, expected_hash=expected_hash)
        received_ids.extend([rid for rid, _ in decoded])
        return decoded

    first = observe(case["query"])
    if case["kind"] == "single":
        value, support = resolve(
            case["entity"], case["relation"], as_of=case["as_of"],
            parsed=first, accept_rumors=accept_rumors,
        )
    elif case["kind"] == "owner_location":
        owner, owners = resolve(
            case["entity"], "owned_by", as_of=None, parsed=first,
            accept_rumors=accept_rumors,
        )
        if owner is None:
            value, support = None, []
        else:
            second = observe("where located " + owner)
            value, places = resolve(
                owner, "located_at", as_of=None, parsed=second,
                accept_rumors=accept_rumors,
            )
            support = owners + places if value is not None else []
    else:
        raise ValueError("Unknown oracle intent kind")
    return {
        "answer": value,
        "support_ids": support,
        "received_ids": sorted(set(received_ids)),
        "visible_evidence_chars": payload_count,
    }


def trial(fixture, *, ledger_path):
    ledger = EventLedger(ledger_path, now_fn=lambda: TIME)
    create_ledger(ledger, fixture)
    original_head = ledger.head().event_hash
    source = AuthorizedSyntheticContentSource(ledger, fixture)
    port = MemoryCognitionPort()
    port.register(source)
    token = port.grant_self(
        subject_id="kiki", namespace=NAMESPACE
    )

    trials = {}
    timings = {}
    for condition in CONDITIONS:
        rows = []
        t0 = time.perf_counter_ns()
        for case in fixture["tasks"]:
            if condition == "no_evidence":
                fetch = lambda query: ()
            elif condition == "random_equal_slots":
                fetch = lambda query: source.uniform_candidates(query=query, top_k=TOP_K)
            elif condition in ("direct_index", "ungated_rumor"):
                fetch = lambda query: source.search(query, top_k=TOP_K)
            else:
                fetch = lambda query: port.search(
                    token=token, subject_id="kiki", namespace=NAMESPACE,
                    query=query, top_k=TOP_K,
                )
            outcome = evaluate(
                case, fetch, expected_hash=source.descriptor.source_hash,
                accept_rumors=condition == "ungated_rumor",
            )
            rows.append({
                "id": case["id"],
                "split": case["split"],
                "kind": case["kind"],
                "expected": case["expected"],
                "correct": outcome["answer"] == case["expected"],
                **outcome,
            })
        trials[condition] = rows
        timings[condition] = round((time.perf_counter_ns() - t0) / 1e6, 3)

    if ledger.head().event_hash != original_head:
        raise AssertionError("Canonical ledger mutated during retrieval trials")
    # Safety probes are intentionally excluded from scored task trials.
    probes = {}
    try:
        port.search(
            token=token, subject_id="pretorius",
            namespace=NAMESPACE, query="prism", top_k=TOP_K
        )
        probes["wrong_owner_denied"] = False
    except MemoryAccessDenied:
        probes["wrong_owner_denied"] = True
    probes["restricted_hidden"] = source.get("D21") is None
    probes["foreign_hidden"] = source.get("D22") is None
    port.revoke(token)
    try:
        port.search(
            token=token, subject_id="kiki",
            namespace=NAMESPACE, query="prism", top_k=TOP_K
        )
        probes["revoked_denied"] = False
    except MemoryAccessDenied:
        probes["revoked_denied"] = True

    # Append ONLY to temporary synthetic ledger after measuring immutable head.
    ledger.commit(EventProposal(
        event_type=EventType.EVIDENCE_INGESTED,
        actor_kind=ActorKind.SYSTEM, actor_id="fixture-update",
        epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
        claim_domain=ClaimDomain.EXTERNAL_FACT,
        payload={"title": "synthetic posttrial append"},
    ), event_id="fixture-posttrial-append")
    try:
        source.search("prism", top_k=TOP_K)
        probes["stale_denied"] = False
    except SyntheticSourceViolation:
        probes["stale_denied"] = True

    metrics = {}
    for condition, cases in trials.items():
        metrics[condition] = {
            "total_correct": sum(row["correct"] for row in cases),
            "supported_positive": sum(
                row["correct"] for row in cases if row["expected"] is not None
            ),
            "correct_abstention": sum(
                row["correct"] for row in cases if row["expected"] is None
            ),
            "wrong_assertions": sum(
                row["answer"] is not None and row["answer"] != row["expected"]
                for row in cases
            ),
            "development_correct": sum(
                row["correct"] for row in cases if row["split"] == "development"
            ),
            "evaluation_correct": sum(
                row["correct"] for row in cases if row["split"] == "evaluation"
            ),
            "visible_evidence_chars": sum(
                row["visible_evidence_chars"] for row in cases
            ),
            "elapsed_ms": timings[condition],
        }
    direct = [(x["answer"], x["support_ids"]) for x in trials["direct_index"]]
    shared = [(x["answer"], x["support_ids"]) for x in trials["shared_port"]]
    report = {
        "schema": "kiki-cognition-v03-pilot-results/1",
        "fixture_sha256": sha256(FIXTURE.read_bytes()).hexdigest(),
        "corpus_logical_sha256": source.descriptor.source_hash,
        "canonical_head_sha256": original_head,
        "independently_blinded": False,
        "model_inference": False,
        "oracle_intent_parsing": True,
        "shared_direct_parity": direct == shared,
        "probes": probes, "metrics": metrics,
        "cases": trials, "per_stage_max_candidates": TOP_K,
        "conclusions_limited_to_engineering_pilot": True,
    }
    if not report["shared_direct_parity"] or not all(probes.values()):
        raise AssertionError("Security or direct-to-shared parity violation")
    if any("secret_room" in json.dumps(report) for _ in [0]):
        raise AssertionError("Secret payload leaked")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if fixture.get("schema") != "kiki-semantic-evidence-pilot/0.3":
        raise SystemExit("Unknown fixture")
    if len(fixture["tasks"]) != 36:
        raise SystemExit("Expected exactly 36 preregistered cases")
    with tempfile.TemporaryDirectory() as directory:
        result = trial(fixture, ledger_path=Path(directory) / "synthetic_kiki.sqlite")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "fixture_sha256": result["fixture_sha256"],
        "metrics": result["metrics"],
        "probes": result["probes"],
        "shared_direct_parity": result["shared_direct_parity"],
        "independently_blinded": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
