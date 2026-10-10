"""Real Kiki EventLedger + upstream MemoryCognitionPort cross-repository tests.

This file lives outside the ordinary Kiki test discovery tree so a clean
Kiki install retains no hard Pretorius-Connectome runtime dependency.
The dedicated integration workflow checks out the exact upstream commit.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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


class KikiCrossRepositoryMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "synthetic_kiki.db"
        self.ledger = EventLedger(
            self.path, now_fn=lambda: datetime(2026, 10, 9, tzinfo=timezone.utc)
        )
        self.external = self.evidence("SECRET_RAW_TITLE_FROM_EXTERNAL_USER")
        self.encounter = self.ledger.commit(EventProposal(
            event_type=EventType.ENCOUNTER_RECORDED,
            actor_kind=ActorKind.KIKI, actor_id="kiki",
            epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
            claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
            ancestry=(
                AncestryEdge(self.external.event_id, DerivationMode.CAUSAL_PARENT),
            ),
            causal_parent_ids=(self.external.event_id,),
            payload={
                "representation_id": self.external.event_id,
                "encounter_type": "retrieval",
                "mode": "design_history",
                "activation_function_version": "count-activation-v1",
            },
        ))
        self.before_hash = self.ledger.head().event_hash
        self.adapter = KikiLedgerCognitionSource(self.ledger)
        self.port = MemoryCognitionPort()
        self.port.register(self.adapter)
        self.token = self.port.grant_self(
            subject_id="kiki", namespace=NAMESPACE
        )

    def tearDown(self):
        self.tmp.cleanup()

    def evidence(self, title, *, restrictions=frozenset()):
        return self.ledger.commit(EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM,
            actor_id="test-import",
            epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT,
            payload={"title": title},
            content_restrictions=restrictions,
        ))

    def retrieve(self, query):
        return self.port.search(
            token=self.token, subject_id="kiki",
            namespace=NAMESPACE, query=query, top_k=10,
        )

    def test_canonical_event_receipts_retrieved_without_raw_private_content(self):
        encounter = self.retrieve("retrieval encounter")
        self.assertEqual([x.record_id for x in encounter], [self.encounter.event_id])
        self.assertEqual(encounter[0].subject_id, "kiki")
        self.assertEqual(encounter[0].source_hash, self.before_hash)
        self.assertEqual(encounter[0].origin_class, "observed_runtime")
        self.assertEqual(encounter[0].epistemic_status, "candidate_not_entailment")
        self.assertFalse(encounter[0].eligible_for_lived_write)
        self.assertEqual(encounter[0].channel, "external_memory_evidence")
        self.assertNotIn("SECRET_RAW_TITLE", str(encounter))
        receipts = self.retrieve("evidence ingested")
        self.assertEqual(receipts[0].record_id, self.external.event_id)
        self.assertEqual(receipts[0].origin_class, "external_document")
        self.assertNotIn("SECRET_RAW_TITLE", receipts[0].text)
        self.assertEqual(self.ledger.head().event_hash, self.before_hash)

    def test_canonical_history_is_immutable_and_projection_rebuilds(self):
        first = self.retrieve("encounter")
        other = KikiLedgerCognitionSource(EventLedger(self.path))
        self.assertEqual(other.descriptor, self.adapter.descriptor)
        self.assertEqual(other.search("encounter", top_k=5)[0].record_id,
                         first[0].record_id)
        self.assertEqual(self.ledger.head().event_hash, self.before_hash)
        self.ledger.verify_integrity()
        self.assertEqual(list(Path(self.tmp.name).glob("*.db")),
                         [self.path])  # no second DB introduced

    def test_subject_swap_or_cross_project_autobiography_is_denied(self):
        with self.assertRaises(MemoryAccessDenied):
            self.port.grant_self(subject_id="pretorius", namespace=NAMESPACE)
        with self.assertRaises(MemoryAccessDenied):
            self.port.search(
                token=self.token, subject_id="pretorius",
                namespace=NAMESPACE, query="encounter",
            )
        with self.assertRaises(MemoryAccessDenied):
            self.port.search(
                token=self.token, subject_id="kiki",
                namespace="pretorius.reconstructed.v12", query="encounter",
            )
        self.assertEqual(self.ledger.head().event_hash, self.before_hash)

    def test_restricted_canonical_evidence_is_never_indexed(self):
        denied = self.evidence(
            "SECRET_BLOCKED_INFORMATION",
            restrictions=frozenset((Restriction.FORBID_CANONICAL_EXPERIENCE,)),
        )
        fresh = KikiLedgerCognitionSource(self.ledger)
        self.assertIsNone(fresh.get(denied.event_id))
        self.assertEqual(fresh.search("secret", top_k=5), [])
        self.assertNotIn("SECRET_BLOCKED", str(fresh.search("evidence", top_k=5)))

    def test_append_invalidates_snapshot_and_old_capability(self):
        self.evidence("Additional synthetic receipt")
        with self.assertRaises(StaleLedgerProjection):
            self.retrieve("encounter")
        with self.assertRaises(StaleLedgerProjection):
            self.port.get(
                token=self.token, subject_id="kiki",
                namespace=NAMESPACE, record_id=self.encounter.event_id,
            )
        # Rebuild against the new canonical head rather than editing old state.
        fresh = KikiLedgerCognitionSource(self.ledger)
        other_port = MemoryCognitionPort()
        other_port.register(fresh)
        new_token = other_port.grant_self(subject_id="kiki", namespace=NAMESPACE)
        self.assertNotEqual(fresh.descriptor.source_hash, self.before_hash)
        self.assertEqual(
            other_port.search(token=new_token, subject_id="kiki",
                              namespace=NAMESPACE, query="encounter")[0].record_id,
            self.encounter.event_id,
        )

    def test_revoke_blocks_retrieval_and_hydration(self):
        self.port.revoke(self.token)
        with self.assertRaises(MemoryAccessDenied):
            self.retrieve("encounter")
        with self.assertRaises(MemoryAccessDenied):
            self.port.get(token=self.token, subject_id="kiki",
                          namespace=NAMESPACE, record_id=self.encounter.event_id)

    def test_unknown_record_cannot_be_fabricated(self):
        self.assertIsNone(self.port.get(
            token=self.token, subject_id="kiki",
            namespace=NAMESPACE, record_id="nonexistent-event",
        ))
        self.assertEqual(self.retrieve("galactic teleporter"), [])

    def test_two_independent_processes_reproduce_identical_snapshot(self):
        script = (
            "import json,sys;"
            "from runtime.kiki_mind.ledger import EventLedger;"
            "from runtime.kiki_mind.cognition_adapter import KikiLedgerCognitionSource;"
            "a=KikiLedgerCognitionSource(EventLedger(sys.argv[1]));"
            "print(json.dumps([a.descriptor.source_hash,"
            "[(x.record_id,x.source_excerpt) for x in a.search('encounter',top_k=4)]]))"
        )
        outputs = []
        for seed in ("2", "987"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            outputs.append(subprocess.check_output(
                [sys.executable, "-c", script, str(self.path)],
                cwd=Path(__file__).resolve().parents[1], env=env, text=True,
            ).strip())
        self.assertEqual(outputs[0], outputs[1])
        self.assertIn(self.before_hash, outputs[0])


if __name__ == "__main__":
    unittest.main()
