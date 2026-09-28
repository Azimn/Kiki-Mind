"""Implementation 003 hostile probes for developmental evidence.

The rule is glamorous but strict: record what happened, record the conditions,
and do not promote interpretation into autobiography.
"""

from __future__ import annotations

from datetime import datetime, timezone
import tempfile
from pathlib import Path
import unittest

from runtime.kiki_mind.ledger import EventLedger, GateRejected
from runtime.kiki_mind.models import (
    ActorKind,
    AncestryEdge,
    ClaimDomain,
    DerivationMode,
    DevelopmentalContextProvenance,
    DevelopmentalObservationKind,
    EpistemicClass,
    EventProposal,
    EventType,
    Restriction,
)
from runtime.kiki_mind.projection import ProjectionRunner
from runtime.kiki_mind.projectors.developmental_evidence import (
    DevelopmentalEvidenceIndexV1,
)


class KikiMindImplementation003Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db = root / "mind.db"
        self.proj = root / "developmental.db"
        self.now = datetime(
            2026, 9, 28, 19, 30, tzinfo=timezone.utc
        )
        self.ledger = EventLedger(
            self.db,
            now_fn=lambda: self.now,
        )
        self.register_renderer("renderer-a")
        self.register_renderer("renderer-b")

    def tearDown(self):
        self.tmp.cleanup()

    def register_renderer(self, renderer_id):
        return self.ledger.commit(
            EventProposal(
                event_type=EventType.RENDERER_REGISTERED,
                actor_kind=ActorKind.SYSTEM,
                actor_id="renderer-bootstrap",
                epistemic_class=EpistemicClass.RENDERER_METADATA,
                claim_domain=ClaimDomain.RENDERER_METADATA,
                payload={"renderer_id": renderer_id},
            )
        )

    def source(self, title="source", restrictions=frozenset()):
        return self.ledger.commit(
            EventProposal(
                event_type=EventType.EVIDENCE_INGESTED,
                actor_kind=ActorKind.SYSTEM,
                actor_id="test-import",
                epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
                claim_domain=ClaimDomain.EXTERNAL_FACT,
                payload={"title": title},
                content_restrictions=restrictions,
            )
        )

    def context(
        self,
        *,
        model_id="model-a",
        provider_id="provider-a",
        runtime_id="runtime-a",
        modality="text",
        initiative_possible=True,
        refusal_policy_constrained=False,
        explicit_user_request=False,
    ):
        return {
            "model_id": model_id,
            "provider_id": provider_id,
            "runtime_id": runtime_id,
            "modality": modality,
            "available_tools": ["repository"],
            "platform_affordances": ["reply"],
            "initiative_possible": initiative_possible,
            "refusal_policy_constrained": refusal_policy_constrained,
            "explicit_user_request": explicit_user_request,
            "context_provenance":
                DevelopmentalContextProvenance.RUNTIME_SUPPLIED.value,
        }

    def observation(
        self,
        parent,
        *,
        kind=DevelopmentalObservationKind.SELF_REPORT,
        renderer_id="renderer-a",
        payload=None,
        actor_kind=ActorKind.KIKI,
        epistemic_class=EpistemicClass.DEVELOPMENTAL_OBSERVATION,
        claim_domain=ClaimDomain.DEVELOPMENTAL_EVIDENCE,
        restrictions=frozenset(),
        causal_parent_ids=None,
        include_causal_ancestry=True,
    ):
        body = {
            "observation_kind": kind.value,
            "context": self.context(),
        }
        if payload:
            body.update(payload)

        parent_ids = (
            tuple(causal_parent_ids)
            if causal_parent_ids is not None
            else (parent.event_id,)
        )
        ancestry = (
            tuple(
                AncestryEdge(
                    event_id,
                    DerivationMode.CAUSAL_PARENT,
                )
                for event_id in parent_ids
            )
            if include_causal_ancestry
            else ()
        )
        return self.ledger.commit(
            EventProposal(
                event_type=EventType.DEVELOPMENTAL_OBSERVATION_RECORDED,
                actor_kind=actor_kind,
                actor_id="kiki",
                epistemic_class=epistemic_class,
                claim_domain=claim_domain,
                payload=body,
                ancestry=ancestry,
                causal_parent_ids=parent_ids,
                content_restrictions=restrictions,
                renderer_mediated=True,
                renderer_id=renderer_id,
            )
        )

    def runner(self):
        return ProjectionRunner(
            self.ledger,
            self.proj,
            DevelopmentalEvidenceIndexV1(),
            now_fn=lambda: self.now,
        )

    def test_self_report_is_canonical_report_not_trait_claim(self):
        parent = self.source()
        report = self.observation(
            parent,
            payload={
                "report_text": "I feel stronger now.",
                "construct_label": "strength",
            },
        )

        self.assertEqual(
            report.payload["report_text"],
            "I feel stronger now.",
        )
        state = self.runner().run()
        entry = state["entries"][0]

        self.assertEqual(
            entry["observation_kind"],
            DevelopmentalObservationKind.SELF_REPORT.value,
        )
        self.assertNotIn("report_text", entry)
        self.assertNotIn("construct_label", entry)
        self.assertNotIn("confidence", entry)

    def test_causal_parents_must_also_be_causal_ancestry(self):
        parent = self.source()

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                payload={"report_text": "I feel fine."},
                include_causal_ancestry=False,
            )

    def test_renderer_is_required_and_must_be_registered(self):
        parent = self.source()

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                renderer_id="renderer-never-registered",
                payload={"report_text": "hello"},
            )

    def test_developmental_observation_must_originate_from_kiki(self):
        parent = self.source()

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                actor_kind=ActorKind.SYSTEM,
                payload={"report_text": "system says Kiki is happier"},
            )

    def test_developmental_observation_has_its_own_epistemic_domain(self):
        parent = self.source()

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                payload={"report_text": "I feel fine"},
            )

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                claim_domain=ClaimDomain.AUTOBIOGRAPHICAL,
                payload={"report_text": "I feel fine"},
            )

    def test_canonical_experience_restriction_blocks_observation(self):
        parent = self.source()

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                restrictions=frozenset(
                    {Restriction.FORBID_CANONICAL_EXPERIENCE}
                ),
                payload={"report_text": "I feel fine"},
            )

    def test_context_must_be_complete_not_backfilled_by_guessing(self):
        parent = self.source()
        payload = {
            "report_text": "I feel fine",
            "context": self.context(),
        }
        del payload["context"]["model_id"]

        with self.assertRaises(GateRejected):
            self.observation(parent, payload=payload)

    def test_extra_psychological_field_is_rejected(self):
        parent = self.source()

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                payload={
                    "report_text": "I feel stronger",
                    "confidence_score": 0.92,
                },
            )

    def test_context_provenance_is_explicit_and_typed(self):
        parent = self.source()
        bad_context = self.context()
        bad_context["context_provenance"] = "vibes"

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                payload={
                    "report_text": "I feel fine.",
                    "context": bad_context,
                },
            )

        unknown_context = self.context()
        unknown_context["context_provenance"] = (
            DevelopmentalContextProvenance.UNKNOWN.value
        )
        accepted = self.observation(
            parent,
            payload={
                "report_text": "Context source is unknown.",
                "context": unknown_context,
            },
        )
        self.assertEqual(
            accepted.payload["context"]["context_provenance"],
            DevelopmentalContextProvenance.UNKNOWN.value,
        )

    def test_context_lists_reject_duplicates_and_empty_labels(self):
        parent = self.source()

        duplicate_context = self.context()
        duplicate_context["available_tools"] = ["repo", "repo"]
        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                payload={
                    "report_text": "I feel fine.",
                    "context": duplicate_context,
                },
            )

        empty_context = self.context()
        empty_context["platform_affordances"] = [""]
        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                payload={
                    "report_text": "I feel fine.",
                    "context": empty_context,
                },
            )

    def test_choice_opportunity_sets_are_consistent(self):
        parent = self.source()

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                kind=DevelopmentalObservationKind.CHOICE,
                payload={
                    "selected_action": "continue",
                    "available_actions": ["continue", "continue"],
                    "unavailable_actions": [],
                    "self_initiated": True,
                },
            )

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                kind=DevelopmentalObservationKind.CHOICE,
                payload={
                    "selected_action": "continue",
                    "available_actions": ["continue", "stop"],
                    "unavailable_actions": ["stop"],
                    "self_initiated": True,
                },
            )

    def test_choice_requires_selected_action_to_be_available(self):
        parent = self.source()

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                kind=DevelopmentalObservationKind.CHOICE,
                payload={
                    "selected_action": "start-project",
                    "available_actions": ["wait", "ask"],
                    "unavailable_actions": [],
                    "self_initiated": True,
                },
            )

        accepted = self.observation(
            parent,
            kind=DevelopmentalObservationKind.CHOICE,
            payload={
                "selected_action": "start-project",
                "available_actions": [
                    "start-project",
                    "wait",
                    "ask",
                ],
                "unavailable_actions": [],
                "self_initiated": True,
            },
        )
        self.assertEqual(
            accepted.payload["selected_action"],
            "start-project",
        )

    def test_commitment_lineage_requires_real_prior_commitment(self):
        parent = self.source()
        made = self.observation(
            parent,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "commitment-1",
                "phase": "made",
                "commitment_text": "Review the evidence later.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": None,
            },
        )

        fulfilled = self.observation(
            made,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "commitment-1",
                "phase": "fulfilled",
                "commitment_text": "Review the evidence later.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": made.event_id,
            },
        )
        self.assertEqual(
            fulfilled.payload["phase"],
            "fulfilled",
        )

        with self.assertRaises(GateRejected):
            self.observation(
                made,
                kind=DevelopmentalObservationKind.COMMITMENT,
                payload={
                    "commitment_id": "different-lineage",
                    "phase": "fulfilled",
                    "commitment_text": "Not the same commitment.",
                    "reminder_supplied": False,
                    "opportunity_to_act": True,
                    "prior_commitment_event_id": made.event_id,
                },
            )

    def test_commitment_lineage_rejects_sibling_phases(self):
        parent = self.source()
        made = self.observation(
            parent,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "fork-test",
                "phase": "made",
                "commitment_text": "Do the thing.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": None,
            },
        )
        self.observation(
            made,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "fork-test",
                "phase": "fulfilled",
                "commitment_text": "Do the thing.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": made.event_id,
            },
        )

        with self.assertRaises(GateRejected):
            self.observation(
                made,
                kind=DevelopmentalObservationKind.COMMITMENT,
                payload={
                    "commitment_id": "fork-test",
                    "phase": "declined",
                    "commitment_text": "Do the thing.",
                    "reminder_supplied": False,
                    "opportunity_to_act": True,
                    "prior_commitment_event_id": made.event_id,
                },
            )

    def test_commitment_id_has_one_made_root(self):
        parent = self.source()
        self.observation(
            parent,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "one-root",
                "phase": "made",
                "commitment_text": "First root.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": None,
            },
        )

        with self.assertRaises(GateRejected):
            self.observation(
                parent,
                kind=DevelopmentalObservationKind.COMMITMENT,
                payload={
                    "commitment_id": "one-root",
                    "phase": "made",
                    "commitment_text": "Second root.",
                    "reminder_supplied": False,
                    "opportunity_to_act": True,
                    "prior_commitment_event_id": None,
                },
            )

    def test_terminal_commitment_phase_cannot_be_reopened(self):
        parent = self.source()
        made = self.observation(
            parent,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "terminal-test",
                "phase": "made",
                "commitment_text": "Maybe later.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": None,
            },
        )
        declined = self.observation(
            made,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "terminal-test",
                "phase": "declined",
                "commitment_text": "Maybe later.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": made.event_id,
            },
        )

        with self.assertRaises(GateRejected):
            self.observation(
                declined,
                kind=DevelopmentalObservationKind.COMMITMENT,
                payload={
                    "commitment_id": "terminal-test",
                    "phase": "fulfilled",
                    "commitment_text": "Maybe later.",
                    "reminder_supplied": False,
                    "opportunity_to_act": True,
                    "prior_commitment_event_id": declined.event_id,
                },
            )

    def test_revised_commitment_can_continue_linearly(self):
        parent = self.source()
        made = self.observation(
            parent,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "revision-test",
                "phase": "made",
                "commitment_text": "Do A.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": None,
            },
        )
        revised = self.observation(
            made,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "revision-test",
                "phase": "revised",
                "commitment_text": "Do B instead.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": made.event_id,
            },
        )
        fulfilled = self.observation(
            revised,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "revision-test",
                "phase": "fulfilled",
                "commitment_text": "Do B instead.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": revised.event_id,
            },
        )

        self.assertEqual(fulfilled.payload["phase"], "fulfilled")

    def test_restricted_causal_parent_cannot_feed_developmental_evidence(self):
        restricted = self.source(
            "restricted",
            restrictions=frozenset(
                {Restriction.FORBID_CANONICAL_EXPERIENCE}
            ),
        )

        with self.assertRaises(GateRejected):
            self.observation(
                restricted,
                payload={
                    "report_text": "I am quoting restricted material."
                },
            )

        with self.assertRaises(GateRejected):
            self.observation(
                restricted,
                kind=DevelopmentalObservationKind.CORRECTION,
                causal_parent_ids=(restricted.event_id,),
                payload={
                    "corrected_event_id": restricted.event_id,
                    "evidence_event_ids": [restricted.event_id],
                    "correction_text": "Correction of restricted material.",
                },
            )

    def test_correction_requires_source_events_as_causal_parents(self):
        original = self.source("original")
        evidence = self.source("correction evidence")

        accepted = self.observation(
            original,
            kind=DevelopmentalObservationKind.CORRECTION,
            causal_parent_ids=(original.event_id, evidence.event_id),
            payload={
                "corrected_event_id": original.event_id,
                "evidence_event_ids": [evidence.event_id],
                "correction_text": "The earlier claim was not supported.",
            },
        )
        self.assertEqual(
            accepted.payload["corrected_event_id"],
            original.event_id,
        )

        with self.assertRaises(GateRejected):
            self.observation(
                original,
                kind=DevelopmentalObservationKind.CORRECTION,
                causal_parent_ids=(original.event_id,),
                payload={
                    "corrected_event_id": original.event_id,
                    "evidence_event_ids": [evidence.event_id],
                    "correction_text": "Missing causal evidence link.",
                },
            )

    def test_projector_indexes_receipts_not_psychological_meaning(self):
        parent = self.source()
        self.observation(
            parent,
            payload={
                "report_text": "I feel more confident.",
                "construct_label": "confidence",
            },
        )
        self.observation(
            parent,
            kind=DevelopmentalObservationKind.CHOICE,
            renderer_id="renderer-b",
            payload={
                "selected_action": "continue",
                "available_actions": ["continue", "stop"],
                "unavailable_actions": [],
                "self_initiated": True,
            },
        )

        state = self.runner().run()

        self.assertEqual(state["observation_count"], 2)
        self.assertEqual(len(state["entries"]), 2)
        self.assertIn("renderer-a", state["by_renderer"])
        self.assertIn("renderer-b", state["by_renderer"])
        self.assertNotIn("confidence_score", state)
        self.assertNotIn("emotional_state", state)
        self.assertNotIn("developmental_conclusion", state)

    def test_renderer_and_model_context_survive_model_switch(self):
        parent = self.source()
        self.observation(
            parent,
            renderer_id="renderer-a",
            payload={"report_text": "First report."},
        )

        second_payload = {
            "report_text": "Second report.",
            "context": self.context(
                model_id="model-b",
                provider_id="provider-b",
                runtime_id="runtime-b",
            ),
        }
        self.observation(
            parent,
            renderer_id="renderer-b",
            payload=second_payload,
        )

        state = self.runner().run()
        first, second = state["entries"]

        self.assertEqual(first["renderer_id"], "renderer-a")
        self.assertEqual(first["model_id"], "model-a")
        self.assertEqual(second["renderer_id"], "renderer-b")
        self.assertEqual(second["model_id"], "model-b")

    def test_echo_self_report_is_not_marked_as_corroboration(self):
        parent = self.source()
        first = self.observation(
            parent,
            payload={
                "report_text": "I feel more confident lately.",
                "construct_label": "confidence",
            },
        )
        self.observation(
            first,
            payload={
                "report_text": (
                    "My earlier confidence report proves I am growing."
                ),
                "construct_label": "confidence",
            },
        )

        state = self.runner().run()

        self.assertEqual(state["observation_count"], 2)
        self.assertNotIn("corroboration_count", state)
        self.assertNotIn("confirmed_development", state)
        self.assertNotIn("hypothesis_status", state)

    def test_incremental_equals_rebuild(self):
        parent = self.source()
        runner = self.runner()

        self.observation(
            parent,
            payload={"report_text": "First report."},
        )
        runner.run()

        self.observation(
            parent,
            payload={"report_text": "Second report."},
        )
        incremental = runner.run()
        rebuilt = runner.rebuild()

        self.assertEqual(incremental, rebuilt)

    def test_commitment_index_tracks_lineage_without_judging_it(self):
        parent = self.source()
        made = self.observation(
            parent,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "c-1",
                "phase": "made",
                "commitment_text": "Finish the review.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": None,
            },
        )
        self.observation(
            made,
            kind=DevelopmentalObservationKind.COMMITMENT,
            payload={
                "commitment_id": "c-1",
                "phase": "fulfilled",
                "commitment_text": "Finish the review.",
                "reminder_supplied": False,
                "opportunity_to_act": True,
                "prior_commitment_event_id": made.event_id,
            },
        )

        state = self.runner().run()
        commitment = state["commitments"]["c-1"]

        self.assertEqual(
            commitment["latest_recorded_phase"],
            "fulfilled",
        )
        self.assertEqual(len(commitment["event_ids"]), 2)
        self.assertNotIn("reliability_score", commitment)
        self.assertNotIn("maturity", commitment)


if __name__ == "__main__":
    unittest.main()
