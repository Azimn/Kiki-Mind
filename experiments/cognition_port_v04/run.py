#!/usr/bin/env python3
"""Execute a pinned, externally authored bAbI Q/A benchmark via Kiki's port.

This is a non-LLM, fixed grammar pilot. Gold answers and supporting fact IDs
are read by the scorer only AFTER every candidate decision is complete.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pretorius_connectome.cognition_port import MemoryAccessDenied, MemoryCognitionPort
from runtime.kiki_mind.ledger import EventLedger
from runtime.kiki_mind.models import ActorKind, ClaimDomain, EpistemicClass, EventProposal, EventType
from experiments.cognition_port_v04.reader import reason
from experiments.cognition_port_v04.source import (
    BabiKikiSource, ORIGINAL, NAMESPACE, REVISION, load_babi, record_id, blob_sha,
)

VERSION = "kiki-external-babi-nloracle/0.4"
UPSTREAM_INTERFACE = "cc82c72167d87c19f16125ccdf9477b53c777878"
SELECTION_PER_TASK = 40
TOP_K = 5
CLOCK = datetime(2026, 10, 10, 14, 0, tzinfo=timezone.utc)
CONDITIONS = (
    "no_context","full_context","random_five","native_ranked","shared_ranked"
)


def ledger_for_question(path, question, *, source_blob):
    ledger = EventLedger(path, now_fn=lambda: CLOCK)
    for n, text in question.facts:
        # A source receipt is NOT a lived memory.
        ledger.commit(EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM,
            actor_id="external-public-benchmark-v04",
            epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT,
            payload={
                "title": text, "text": text,
                "source_owner": "kiki", "source_blob": source_blob, "line": n,
                "benchmark_task": question.task, "benchmark_episode": question.episode,
            },
        ), event_id=record_id(question,n))
    ledger.verify_integrity()
    return ledger


def evaluate(question, source, port, token):
    outputs = {}
    for mode in CONDITIONS:
        t0 = time.perf_counter_ns()
        if mode == "no_context":
            rows = ()
        elif mode == "full_context":
            rows = source.records()
        elif mode == "random_five":
            rows = source.random_candidates(question.question, top_k=TOP_K)
        elif mode == "native_ranked":
            rows = source.search(question.question, top_k=TOP_K)
        elif mode == "shared_ranked":
            rows = port.search(
                token=token, subject_id="kiki", namespace=NAMESPACE,
                query=question.question, top_k=TOP_K,
            )
        else:
            raise AssertionError("Unregistered arm")
        value = reason(question.question, rows)
        outputs[mode] = {
            "prediction": value.value,
            "cited_source_ids": list(value.cited),
            "parser_supported": value.parser_supported,
            "received_source_ids": [c.record_id for c in rows],
            "chars_seen": sum(len(getattr(c,"text",None) or c.source_excerpt) for c in rows),
            "elapsed_ms": round((time.perf_counter_ns()-t0)/1e6,4),
        }
        if not set(value.cited).issubset(set(outputs[mode]["received_source_ids"])):
            raise AssertionError("Citations escape retrieved source records")
        if any(not (sid.startswith(f"{question.task}-{question.ordinal:04d}-")
                    and int(sid.rsplit("-",1)[-1])<question.line)
               for sid in outputs[mode]["received_source_ids"]):
            raise AssertionError("Cross-episode or future source leaked")
        if any(getattr(row,"eligible_for_lived_write",False) for row in rows):
            raise AssertionError("External source illegally admitted to lived memory")

    direct = outputs["native_ranked"]
    via = outputs["shared_ranked"]
    for field in ("prediction","cited_source_ids","received_source_ids","chars_seen"):
        if direct[field] != via[field]:
            raise AssertionError("Shared port changed answer/evidence compared with same source")

    # Independent scoring AFTER predictions. These fields are never returned to
    # reason() or source.search().
    support_ids = {record_id(question, i) for i in question.support}
    for output in outputs.values():
        output["correct"] = (
            output["prediction"] is not None
            and output["prediction"].casefold()==question.gold_answer.casefold()
        )
        output["gold_support_recall"] = (
            len(support_ids.intersection(output["received_source_ids"])) / len(support_ids)
            if support_ids else None
        )
    return outputs


def safety_probes(q, source, port, token, ledger):
    checks = {}
    try:
        port.search(token=token, subject_id="pretorius",
                    namespace=NAMESPACE,query=q.question,top_k=TOP_K)
        checks["wrong_owner_denied"] = False
    except MemoryAccessDenied:
        checks["wrong_owner_denied"] = True

    port.revoke(token)
    try:
        port.search(token=token, subject_id="kiki",
                    namespace=NAMESPACE,query=q.question,top_k=TOP_K)
        checks["revoked_denied"] = False
    except MemoryAccessDenied:
        checks["revoked_denied"] = True

    # A source can't look ahead: it was constructed with only a question's
    # prefix. Exact lookup of a future source ID cannot succeed.
    checks["future_fact_absent"] = source.get(record_id(q,q.line+1)) is None
    checks["namespace_prefix_only"] = all(
        source.get(record_id(q,i)) is None for i in (q.line, q.line+1, q.line+2)
    )
    before = ledger.head().event_hash
    ledger.commit(EventProposal(
        event_type=EventType.EVIDENCE_INGESTED,actor_kind=ActorKind.SYSTEM,
        actor_id="synthetic-probe",epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
        claim_domain=ClaimDomain.EXTERNAL_FACT,
        payload={"title":"post-trial synthetic append"},
    ),event_id="posttrial-source-change")
    from pretorius_connectome.cognition_port import MemorySourceMismatch
    try:
        source.search(q.question,top_k=TOP_K)
        checks["stale_snapshot_denied"] = False
    except MemorySourceMismatch:
        checks["stale_snapshot_denied"] = True
    checks["synthetic_probe_changes_head_after_scoring"] = ledger.head().event_hash!=before
    return checks


def run(data_dir: Path, *, output: Path, limit=SELECTION_PER_TASK):
    cases = []
    source_shas = {}
    safety = None
    task_sizes = {}
    with tempfile.TemporaryDirectory() as temp:
        for task,(filename,sha) in ORIGINAL.items():
            path = data_dir / filename
            questions = load_babi(path,task=task,limit=limit)
            task_sizes[task] = len(questions)
            source_shas[task] = sha
            for q in questions:
                ledger=ledger_for_question(
                    Path(temp)/f"{task}-{q.ordinal:04d}.sqlite",q,source_blob=sha
                )
                original_head = ledger.head().event_hash
                source=BabiKikiSource(ledger,q,source_blob=sha)
                port=MemoryCognitionPort()
                port.register(source)
                token=port.grant_self(subject_id="kiki",namespace=NAMESPACE)
                predictions=evaluate(q,source,port,token)
                if ledger.head().event_hash != original_head:
                    raise AssertionError("A scoring trial changed canonical source")
                if safety is None:
                    safety=safety_probes(q,source,port,token,ledger)
                else:
                    port.revoke(token)
                cases.append({
                    "case_id":f"{task}-{q.ordinal:04d}",
                    "task":task,"episode":q.episode,
                    "question":q.question,
                    "gold":q.gold_answer,
                    "gold_support_ids":[record_id(q,i) for i in q.support],
                    "prefix_sentence_count":len(q.facts),
                    "outcomes":predictions,
                })
    metrics={}
    for condition in CONDITIONS:
        bytask={}
        for task in ORIGINAL:
            subset=[c["outcomes"][condition] for c in cases if c["task"]==task]
            bytask[task]={
                "n":len(subset),
                "exact_correct":sum(o["correct"] for o in subset),
                "abstain":sum(o["prediction"] is None for o in subset),
                "parser_coverage":sum(o["parser_supported"] for o in subset),
                "support_recall_mean":round(sum(o["gold_support_recall"] for o in subset)/len(subset),4),
                "evidence_chars_total":sum(o["chars_seen"] for o in subset),
                "latency_ms_total":round(sum(o["elapsed_ms"] for o in subset),3),
            }
        metrics[condition]=bytask
    report={
        "schema":VERSION,"selection":{"first_test_questions_per_task":limit,"tasks":list(ORIGINAL)},
        "dataset_repository":"azreasoners/LLM-ASP",
        "dataset_revision":REVISION,"dataset_file_git_blobs":source_shas,
        "independently_authored_dataset":True,
        "public_not_blind_test":True,
        "no_gold_or_intent_in_decision":True,
        "no_llm_or_neural_model":True,
        "original_Kiki_canonical_ledger_unchanged":True,
        "source_lived_write":False,
        "shared_native_parity":True,
        "safety_probes":safety,"metrics":metrics,"cases":cases,
    }
    assert all(safety.values()),safety
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "task_counts":task_sizes,"source_git_blobs":source_shas,
        "metrics":{k:{t:{a:v[a] for a in ("n","exact_correct","abstain","support_recall_mean")}
                       for t,v in m.items()} for k,m in metrics.items()},
        "safety_probes":safety,"shared_native_parity":True,
        "not_semantic_or_blind_validation":True,
    },sort_keys=True,indent=2))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path("results/cognition_port_v04/RESULTS.json"))
    args=p.parse_args()
    run(args.data_dir,output=args.output)


if __name__ == "__main__":
    main()
