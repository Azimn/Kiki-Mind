import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.kiki_mind import (
    ActorKind, ClaimDomain, EpistemicClass, EventLedger, EventProposal,
    EventType, GateRejected, Restriction,
)
from runtime.kiki_mind.retrieval import (
    ConstitutionalComponent, ConstitutionalContextMissing, RetrievalBindingMismatch,
    RetrievalCorruption, RetrievalProjection, RetrievalRegime,
    SubjectiveFrameBuilder, TokenOverlapPolicy, renderer_proposal,
)


class ReversePolicy(TokenOverlapPolicy):
    version = "reverse-v1"
    def rank(self, query, items):
        return tuple(reversed(super().rank(query, items)))


class Implementation004Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.ledger = EventLedger(root / "ledger.sqlite")
        self.index_path = root / "retrieval.json"
        self.regime = RetrievalRegime(
            projector_id="canonical-event-view",
            projector_version="1",
            retrieval_version="004.0",
            embedding_id="offline-token-overlap",
            embedding_version="1",
            chunking_version="event-v1",
            policy_version="token-overlap-v1",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, text, *, epistemic=EpistemicClass.SOURCE_EVIDENCE,
               claim=ClaimDomain.EXTERNAL_FACT, restrictions=frozenset()):
        return self.ledger.commit(EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM,
            actor_id="fixture",
            epistemic_class=epistemic,
            claim_domain=claim,
            payload={"text": text},
            content_restrictions=restrictions,
        ))

    def projection(self, regime=None):
        return RetrievalProjection(self.ledger, self.index_path, regime or self.regime)

    def constitution(self):
        return [
            ConstitutionalComponent("authority", "1", "Renderer has proposal authority only."),
            ConstitutionalComponent("provenance", "1", "Preserve epistemic provenance."),
        ]

    def builder(self, projection):
        return SubjectiveFrameBuilder(
            self.ledger, projection,
            required_constitution={"authority": "1", "provenance": "1"},
        )

    def test_rebuild_after_deletion_is_equivalent(self):
        self.source("red key on table")
        p = self.projection()
        first = p.rebuild()
        self.index_path.unlink()
        second = p.rebuild()
        self.assertEqual(first, second)

    def test_incremental_equals_full_at_same_head(self):
        self.source("first encounter")
        p = self.projection()
        p.rebuild()
        self.source("second encounter")
        incremental = p.incremental()
        self.index_path.unlink()
        rebuilt = p.rebuild()
        self.assertEqual(incremental, rebuilt)

    def test_retrieval_policy_changes_access_not_authority(self):
        a = self.source("glass water kitchen")
        b = self.source("travel book desk")
        p = self.projection(); p.rebuild()
        builder = self.builder(p)
        kwargs = dict(
            query="glass water", constitution=self.constitution(),
            renderer_id="r", renderer_adapter_version="a1", session_id="s",
            budget_chars=10000,
        )
        normal = builder.build(policy=TokenOverlapPolicy(), **kwargs)
        reverse = builder.build(policy=ReversePolicy(), **kwargs)
        nenv = {x.record_id: x.envelope for x in normal.items if x.envelope}
        renv = {x.record_id: x.envelope for x in reverse.items if x.envelope}
        self.assertEqual(nenv, renv)
        self.assertEqual(nenv[f"event:{a.event_id}"].source_event_id, a.event_id)
        self.assertEqual(nenv[f"event:{b.event_id}"].source_event_id, b.event_id)

    def test_renderer_substitution_does_not_change_structured_items(self):
        self.source("persistent memory")
        p = self.projection(); p.rebuild()
        builder = self.builder(p)
        common = dict(query="memory", constitution=self.constitution(),
                      policy=TokenOverlapPolicy(), session_id="same",
                      budget_chars=10000)
        a = builder.build(renderer_id="local-a", renderer_adapter_version="ollama-v1", **common)
        b = builder.build(renderer_id="hosted-b", renderer_adapter_version="hosted-v1", **common)
        self.assertEqual(a.items, b.items)
        self.assertNotEqual(a.receipt.frame_id, b.receipt.frame_id)

    def test_embedding_migration_rejects_old_index(self):
        self.source("memory")
        self.projection().rebuild()
        changed = replace(self.regime, embedding_version="2")
        with self.assertRaises(RetrievalBindingMismatch):
            self.projection(changed).load()

    def test_corruption_never_changes_canon_and_rebuild_recovers(self):
        event = self.source("receipt")
        p = self.projection(); p.rebuild()
        before = self.ledger.head().event_hash
        self.index_path.write_text("{gross", encoding="utf-8")
        with self.assertRaises(RetrievalCorruption):
            p.load()
        self.assertEqual(self.ledger.head().event_hash, before)
        p.rebuild()
        self.assertEqual(p.items()[0].envelope.source_event_id, event.event_id)

    def test_provenance_collision_is_not_deduplicated_or_promoted(self):
        lived = self.source(
            "I found the red key",
            epistemic=EpistemicClass.HISTORICAL_INTERACTION,
            claim=ClaimDomain.DESIGN_HISTORY,
        )
        synthetic = self.source(
            "I found the red key",
            epistemic=EpistemicClass.SYNTHETIC_DESIGN,
            claim=ClaimDomain.DESIGN_HISTORY,
            restrictions=frozenset({Restriction.FORBID_AUTOBIOGRAPHY}),
        )
        p = self.projection(); p.rebuild()
        frame = self.builder(p).build(
            query="red key", constitution=self.constitution(),
            policy=TokenOverlapPolicy(), renderer_id="r",
            renderer_adapter_version="a", session_id="s", budget_chars=10000,
        )
        hits = {x.record_id: x for x in frame.items if x.envelope}
        self.assertIn(f"event:{lived.event_id}", hits)
        self.assertIn(f"event:{synthetic.event_id}", hits)
        self.assertNotEqual(
            hits[f"event:{lived.event_id}"].envelope.epistemic_class,
            hits[f"event:{synthetic.event_id}"].envelope.epistemic_class,
        )
        self.assertIn("forbid_autobiography",
                      hits[f"event:{synthetic.event_id}"].envelope.content_restrictions)

    def test_always_on_omission_and_budget_fail_closed(self):
        self.source("memory")
        p = self.projection(); p.rebuild()
        b = self.builder(p)
        with self.assertRaises(ConstitutionalContextMissing):
            b.build(query="memory", constitution=self.constitution()[:1],
                    policy=TokenOverlapPolicy(), renderer_id="r",
                    renderer_adapter_version="a", session_id="s")
        with self.assertRaises(ConstitutionalContextMissing):
            b.build(query="memory", constitution=self.constitution(),
                    policy=TokenOverlapPolicy(), renderer_id="r",
                    renderer_adapter_version="a", session_id="s", budget_chars=5)

    def test_stale_projection_fails_closed(self):
        self.source("first")
        p = self.projection(); p.rebuild()
        self.source("second")
        with self.assertRaises(RetrievalBindingMismatch):
            p.items()

    def test_frame_receipt_exactly_binds_exposed_structure(self):
        self.source("water glass")
        p = self.projection(); p.rebuild()
        frame = self.builder(p).build(
            query="glass", constitution=self.constitution(),
            policy=TokenOverlapPolicy(), renderer_id="r",
            renderer_adapter_version="a", session_id="s", budget_chars=10000,
        )
        self.assertEqual(frame.receipt.canonical_sequence, self.ledger.head().sequence)
        self.assertEqual(frame.receipt.canonical_tail_hash, self.ledger.head().event_hash)
        self.assertTrue(frame.receipt.structured_frame_digest)
        self.assertEqual(len(frame.receipt.selected_record_ids), 1)

    def test_renderer_cannot_bypass_transition_gate(self):
        proposal = EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.RENDERER,
            actor_id="unregistered-renderer",
            epistemic_class=EpistemicClass.HISTORICAL_INTERACTION,
            claim_domain=ClaimDomain.AUTOBIOGRAPHICAL,
            payload={"text": "I declare this lived."},
            renderer_mediated=False,
        )
        with self.assertRaises(GateRejected):
            renderer_proposal(self.ledger, proposal)
        self.assertIsNone(self.ledger.head())


if __name__ == "__main__":
    unittest.main()
