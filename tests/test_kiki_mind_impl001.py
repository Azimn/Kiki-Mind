from datetime import datetime, timezone
from pathlib import Path
import sqlite3, tempfile, unittest
from runtime.kiki_mind.activation import CountActivationV1
from runtime.kiki_mind.gate import GateFailure, TransitionGate
from runtime.kiki_mind.ledger import EventLedger, GateRejected, IdempotencyConflict
from runtime.kiki_mind.models import (
    ActorKind, AncestryEdge, ClaimDomain, DerivationMode, EpistemicClass,
    EventProposal, EventType, Restriction,
)

NOW = datetime(2026,9,26,14,0,tzinfo=timezone.utc)

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.ledger=EventLedger(Path(self.tmp.name)/"mind.db")
        self.gate=TransitionGate(now_fn=lambda: NOW)
    def tearDown(self): self.tmp.cleanup()
    def commit(self,p): return self.ledger.commit(p,self.gate)

    def evidence(self, synthetic=False):
        return self.commit(EventProposal(
            event_type=EventType.EVIDENCE_INGESTED, actor_kind=ActorKind.SYSTEM,
            actor_id="archaeology-import",
            epistemic_class=EpistemicClass.SYNTHETIC_DESIGN if synthetic else EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.DESIGN_HISTORY if synthetic else ClaimDomain.EXTERNAL_FACT,
            payload={"title":"source"},
            content_restrictions=frozenset({Restriction.FORBID_AUTOBIOGRAPHY}) if synthetic else frozenset(),
        ))

    def renderer(self, rid="renderer-A"):
        return self.commit(EventProposal(
            event_type=EventType.RENDERER_REGISTERED, actor_kind=ActorKind.SYSTEM,
            actor_id="bootstrap", epistemic_class=EpistemicClass.RENDERER_METADATA,
            claim_domain=ClaimDomain.RENDERER_METADATA, payload={"renderer_id":rid},
        ))

    def lease(self, expiry="2026-09-27T14:00:00+00:00"):
        return self.commit(EventProposal(
            event_type=EventType.OPERATOR_LEASE_GRANTED, actor_kind=ActorKind.SYSTEM,
            actor_id="bootstrap", epistemic_class=EpistemicClass.GOVERNANCE,
            claim_domain=ClaimDomain.GOVERNANCE,
            payload={"operator_id":"operator-1","expires_at":expiry},
        ))

    def test_append_only_and_hash_chain(self):
        a=self.evidence(); b=self.evidence()
        self.assertEqual([x.sequence for x in self.ledger.iter_events()],[1,2])
        self.ledger.verify_integrity()
        conn=sqlite3.connect(self.ledger.path)
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("UPDATE canonical_events SET actor_id='x' WHERE event_id=?",(a.event_id,))
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM canonical_events WHERE event_id=?",(b.event_id,))
        conn.close()

    def test_derived_requires_provenance(self):
        with self.assertRaises(GateRejected) as cm:
            self.commit(EventProposal(
                event_type=EventType.INTERPRETATION_RECORDED, actor_kind=ActorKind.KIKI,
                actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION, payload={"claim":"x"},
            ))
        self.assertIn(GateFailure.PROVENANCE_NOT_CONSERVED,cm.exception.decision.failures)

    def test_taint_inherits_on_content_but_not_reference(self):
        s=self.evidence(True)
        bad=EventProposal(
            event_type=EventType.INTERPRETATION_RECORDED, actor_kind=ActorKind.KIKI,
            actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
            claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
            ancestry=(AncestryEdge(s.event_id,DerivationMode.CONTENT),), payload={"claim":"detail"},
        )
        with self.assertRaises(GateRejected) as cm: self.commit(bad)
        self.assertIn(GateFailure.TAINT_CLOSURE_VIOLATION,cm.exception.decision.failures)

        ok=self.commit(EventProposal(
            event_type=EventType.INTERPRETATION_RECORDED, actor_kind=ActorKind.KIKI,
            actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
            claim_domain=ClaimDomain.DESIGN_HISTORY,
            ancestry=(AncestryEdge(s.event_id,DerivationMode.PROVENANCE_REFERENCE),),
            payload={"claim":"A synthetic design artifact existed."},
        ))
        self.assertNotIn(Restriction.FORBID_AUTOBIOGRAPHY,ok.content_restrictions)

    def test_tainted_content_rejected_as_autobiography(self):
        s=self.evidence(True)
        with self.assertRaises(GateRejected) as cm:
            self.commit(EventProposal(
                event_type=EventType.INTERPRETATION_RECORDED, actor_kind=ActorKind.KIKI,
                actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.AUTOBIOGRAPHICAL,
                ancestry=(AncestryEdge(s.event_id,DerivationMode.CONTENT),),
                content_restrictions=frozenset({Restriction.FORBID_AUTOBIOGRAPHY}),
                payload={"claim":"I went to the mall in 1994."},
            ))
        self.assertIn(GateFailure.CLAIM_DOMAIN_RESTRICTED,cm.exception.decision.failures)

    def test_renderer_attribution(self):
        base=self.evidence()
        with self.assertRaises(GateRejected) as cm:
            self.commit(EventProposal(
                event_type=EventType.INTERPRETATION_RECORDED, actor_kind=ActorKind.KIKI,
                actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
                ancestry=(AncestryEdge(base.event_id,DerivationMode.CONTENT),),
                renderer_mediated=True, renderer_id="unknown", payload={"claim":"x"},
            ))
        self.assertIn(GateFailure.RENDERER_UNKNOWN,cm.exception.decision.failures)
        self.renderer()
        ev=self.commit(EventProposal(
            event_type=EventType.INTERPRETATION_RECORDED, actor_kind=ActorKind.KIKI,
            actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
            claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
            ancestry=(AncestryEdge(base.event_id,DerivationMode.CONTENT),),
            renderer_mediated=True, renderer_id="renderer-A", payload={"claim":"x"},
        ))
        self.assertEqual(ev.renderer_id,"renderer-A")

    def test_activation_must_be_derived_and_mode_specific(self):
        with self.assertRaises(GateRejected) as cm:
            self.commit(EventProposal(
                event_type=EventType.ACTIVATION_SET, actor_kind=ActorKind.KIKI, actor_id="kiki",
                epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION, payload={"value":1.0},
            ))
        self.assertIn(GateFailure.ACTIVATION_DIRECT_WRITE_FORBIDDEN,cm.exception.decision.failures)

        base=self.evidence()
        for mode in ("design_history","design_history","autobiographical"):
            self.commit(EventProposal(
                event_type=EventType.ENCOUNTER_RECORDED, actor_kind=ActorKind.KIKI,
                actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
                ancestry=(AncestryEdge(base.event_id,DerivationMode.CAUSAL_PARENT),),
                causal_parent_ids=(base.event_id,),
                payload={"representation_id":base.event_id,"encounter_type":"retrieval",
                         "mode":mode,"activation_function_version":"count-activation-v1"},
            ))
        values={(v.representation_id,v.mode):v.value for v in CountActivationV1().project(self.ledger.iter_events())}
        self.assertEqual(values[(base.event_id,"design_history")],2.0)
        self.assertEqual(values[(base.event_id,"autobiographical")],1.0)

    def test_encounter_requires_accounting_fields(self):
        base=self.evidence()
        with self.assertRaises(GateRejected) as cm:
            self.commit(EventProposal(
                event_type=EventType.ENCOUNTER_RECORDED, actor_kind=ActorKind.KIKI,
                actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
                ancestry=(AncestryEdge(base.event_id,DerivationMode.CAUSAL_PARENT),),
                causal_parent_ids=(base.event_id,),
                payload={"representation_id":base.event_id,"encounter_type":"retrieval","mode":"design"},
            ))
        self.assertIn(GateFailure.ACCOUNTING_ENTRY_MISSING,cm.exception.decision.failures)

    def test_operator_lease_and_two_party_endorsement(self):
        self.lease()
        proposal=self.commit(EventProposal(
            event_type=EventType.CANONICAL_ENDORSEMENT_PROPOSED, actor_kind=ActorKind.KIKI,
            actor_id="kiki", epistemic_class=EpistemicClass.GOVERNANCE,
            claim_domain=ClaimDomain.GOVERNANCE, payload={"target":"next"},
        ))
        ev=self.commit(EventProposal(
            event_type=EventType.CANONICAL_ENDORSEMENT_AUTHORIZED, actor_kind=ActorKind.OPERATOR,
            actor_id="operator-1", epistemic_class=EpistemicClass.GOVERNANCE,
            claim_domain=ClaimDomain.GOVERNANCE, causal_parent_ids=(proposal.event_id,),
            payload={"proposal_event_id":proposal.event_id,"target":"next"},
        ))
        self.assertEqual(ev.event_type,EventType.CANONICAL_ENDORSEMENT_AUTHORIZED)

    def test_expired_lease_blocks_endorsement(self):
        self.lease("2026-09-25T14:00:00+00:00")
        proposal=self.commit(EventProposal(
            event_type=EventType.CANONICAL_ENDORSEMENT_PROPOSED, actor_kind=ActorKind.KIKI,
            actor_id="kiki", epistemic_class=EpistemicClass.GOVERNANCE,
            claim_domain=ClaimDomain.GOVERNANCE, payload={"target":"next"},
        ))
        with self.assertRaises(GateRejected) as cm:
            self.commit(EventProposal(
                event_type=EventType.CANONICAL_ENDORSEMENT_AUTHORIZED, actor_kind=ActorKind.OPERATOR,
                actor_id="operator-1", epistemic_class=EpistemicClass.GOVERNANCE,
                claim_domain=ClaimDomain.GOVERNANCE, causal_parent_ids=(proposal.event_id,),
                payload={"proposal_event_id":proposal.event_id},
            ))
        self.assertIn(GateFailure.OPERATOR_LEASE_EXPIRED,cm.exception.decision.failures)

    def test_causal_lists_cannot_disagree(self):
        base=self.evidence()
        with self.assertRaises(GateRejected) as cm:
            self.commit(EventProposal(
                event_type=EventType.ENCOUNTER_RECORDED, actor_kind=ActorKind.KIKI,
                actor_id="kiki", epistemic_class=EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
                ancestry=(AncestryEdge(base.event_id,DerivationMode.CAUSAL_PARENT),),
                payload={"representation_id":base.event_id,"encounter_type":"retrieval",
                         "mode":"design","activation_function_version":"count-activation-v1"},
            ))
        self.assertIn(GateFailure.CAUSAL_ORDER_INVALID,cm.exception.decision.failures)

    def test_idempotency(self):
        p=EventProposal(
            event_type=EventType.EVIDENCE_INGESTED, actor_kind=ActorKind.SYSTEM,
            actor_id="importer", epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT, payload={"x":1}, idempotency_key="same",
        )
        a=self.commit(p); b=self.commit(p)
        self.assertEqual(a.event_id,b.event_id)
        self.assertEqual(len(list(self.ledger.iter_events())),1)


    def test_idempotency_key_cannot_alias_different_proposal(self):
        a=EventProposal(
            event_type=EventType.EVIDENCE_INGESTED, actor_kind=ActorKind.SYSTEM,
            actor_id="importer", epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT, payload={"x":1}, idempotency_key="collision",
        )
        b=EventProposal(
            event_type=EventType.EVIDENCE_INGESTED, actor_kind=ActorKind.SYSTEM,
            actor_id="importer", epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT, payload={"x":2}, idempotency_key="collision",
        )
        self.commit(a)
        with self.assertRaises(IdempotencyConflict):
            self.commit(b)

if __name__=="__main__": unittest.main()
