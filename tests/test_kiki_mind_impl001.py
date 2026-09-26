from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from runtime.kiki_mind.activation import CountActivationV1
from runtime.kiki_mind.gate import GateFailure, GateDecision
from runtime.kiki_mind.ledger import (
    EventLedger,
    GateRejected,
    IdempotencyConflict,
    IntegrityError,
)
from runtime.kiki_mind.models import (
    ActorKind,
    AncestryEdge,
    ClaimDomain,
    DerivationMode,
    EpistemicClass,
    EventProposal,
    EventType,
    Restriction,
)


class KikiMindImplementation0011Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "mind.db"
        self.now = datetime(
            2026, 9, 26, 14, 0, tzinfo=timezone.utc
        )
        self.ledger = EventLedger(
            self.db,
            now_fn=lambda: self.now,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, proposal, **kwargs):
        return self.ledger.commit(proposal, **kwargs)

    def evidence(self, *, synthetic=False):
        return self.commit(
            EventProposal(
                event_type=EventType.EVIDENCE_INGESTED,
                actor_kind=ActorKind.SYSTEM,
                actor_id="archaeology-import",
                epistemic_class=(
                    EpistemicClass.SYNTHETIC_DESIGN
                    if synthetic
                    else EpistemicClass.SOURCE_EVIDENCE
                ),
                claim_domain=(
                    ClaimDomain.DESIGN_HISTORY
                    if synthetic
                    else ClaimDomain.EXTERNAL_FACT
                ),
                payload={"title": "source"},
                content_restrictions=(
                    frozenset(
                        {Restriction.FORBID_AUTOBIOGRAPHY}
                    )
                    if synthetic
                    else frozenset()
                ),
            )
        )

    def register_renderer(self, renderer_id="renderer-A"):
        return self.commit(
            EventProposal(
                event_type=EventType.RENDERER_REGISTERED,
                actor_kind=ActorKind.SYSTEM,
                actor_id="runtime-bootstrap",
                epistemic_class=EpistemicClass.RENDERER_METADATA,
                claim_domain=ClaimDomain.RENDERER_METADATA,
                payload={
                    "renderer_id": renderer_id,
                    "family": "test",
                },
            )
        )

    def grant_operator(
        self,
        operator_id="operator-1",
        expires_at=None,
    ):
        expires_at = expires_at or (
            self.now + timedelta(hours=12)
        ).isoformat()
        return self.commit(
            EventProposal(
                event_type=EventType.OPERATOR_LEASE_GRANTED,
                actor_kind=ActorKind.SYSTEM,
                actor_id="runtime-bootstrap",
                epistemic_class=EpistemicClass.GOVERNANCE,
                claim_domain=ClaimDomain.GOVERNANCE,
                payload={
                    "operator_id": operator_id,
                    "expires_at": expires_at,
                },
            )
        )

    def renew_operator(
        self,
        previous_lease_event_id,
        *,
        operator_id="operator-1",
        expires_at=None,
    ):
        expires_at = expires_at or (
            self.now + timedelta(hours=12)
        ).isoformat()
        return self.commit(
            EventProposal(
                event_type=EventType.OPERATOR_LEASE_RENEWED,
                actor_kind=ActorKind.OPERATOR,
                actor_id=operator_id,
                epistemic_class=EpistemicClass.GOVERNANCE,
                claim_domain=ClaimDomain.GOVERNANCE,
                causal_parent_ids=(previous_lease_event_id,),
                payload={
                    "operator_id": operator_id,
                    "expires_at": expires_at,
                    "previous_lease_event_id":
                        previous_lease_event_id,
                },
            )
        )

    def test_append_only_and_hash_chain(self):
        a = self.evidence()
        b = self.evidence()
        self.assertEqual(
            [e.sequence for e in self.ledger.iter_events()],
            [1, 2],
        )
        self.ledger.verify_integrity()

        conn = sqlite3.connect(self.db)
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute(
                """
                UPDATE canonical_events
                SET actor_id='evil'
                WHERE event_id=?
                """,
                (a.event_id,),
            )
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute(
                """
                DELETE FROM canonical_events
                WHERE event_id=?
                """,
                (b.event_id,),
            )
        conn.close()

    def test_derived_interpretation_requires_ancestry(self):
        with self.assertRaises(GateRejected) as cm:
            self.commit(
                EventProposal(
                    event_type=
                        EventType.INTERPRETATION_RECORDED,
                    actor_kind=ActorKind.KIKI,
                    actor_id="kiki",
                    epistemic_class=
                        EpistemicClass.INTERNAL_INTERPRETATION,
                    claim_domain=
                        ClaimDomain.INTERNAL_INTERPRETATION,
                    payload={"claim": "something"},
                )
            )
        self.assertIn(
            GateFailure.PROVENANCE_NOT_CONSERVED,
            cm.exception.decision.failures,
        )

    def test_content_taint_is_hereditary(self):
        synthetic = self.evidence(synthetic=True)
        with self.assertRaises(GateRejected) as cm:
            self.commit(
                EventProposal(
                    event_type=
                        EventType.INTERPRETATION_RECORDED,
                    actor_kind=ActorKind.KIKI,
                    actor_id="kiki",
                    epistemic_class=
                        EpistemicClass.INTERNAL_INTERPRETATION,
                    claim_domain=
                        ClaimDomain.INTERNAL_INTERPRETATION,
                    ancestry=(
                        AncestryEdge(
                            synthetic.event_id,
                            DerivationMode.CONTENT,
                        ),
                    ),
                    payload={"claim": "synthetic detail"},
                )
            )
        self.assertIn(
            GateFailure.TAINT_CLOSURE_VIOLATION,
            cm.exception.decision.failures,
        )

    def test_provenance_reference_does_not_blind_design_history(self):
        synthetic = self.evidence(synthetic=True)
        event = self.commit(
            EventProposal(
                event_type=EventType.INTERPRETATION_RECORDED,
                actor_kind=ActorKind.KIKI,
                actor_id="kiki",
                epistemic_class=
                    EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=ClaimDomain.DESIGN_HISTORY,
                ancestry=(
                    AncestryEdge(
                        synthetic.event_id,
                        DerivationMode.PROVENANCE_REFERENCE,
                    ),
                ),
                payload={
                    "claim":
                        "A synthetic design artifact existed."
                },
            )
        )
        self.assertNotIn(
            Restriction.FORBID_AUTOBIOGRAPHY,
            event.content_restrictions,
        )

    def test_tainted_content_cannot_be_autobiographical(self):
        synthetic = self.evidence(synthetic=True)
        with self.assertRaises(GateRejected) as cm:
            self.commit(
                EventProposal(
                    event_type=
                        EventType.INTERPRETATION_RECORDED,
                    actor_kind=ActorKind.KIKI,
                    actor_id="kiki",
                    epistemic_class=
                        EpistemicClass.INTERNAL_INTERPRETATION,
                    claim_domain=ClaimDomain.AUTOBIOGRAPHICAL,
                    ancestry=(
                        AncestryEdge(
                            synthetic.event_id,
                            DerivationMode.CONTENT,
                        ),
                    ),
                    content_restrictions=frozenset(
                        {Restriction.FORBID_AUTOBIOGRAPHY}
                    ),
                    payload={
                        "claim": "I went to the mall in 1994."
                    },
                )
            )
        self.assertIn(
            GateFailure.CLAIM_DOMAIN_RESTRICTED,
            cm.exception.decision.failures,
        )

    def test_renderer_must_be_registered(self):
        base = self.evidence()
        with self.assertRaises(GateRejected) as cm:
            self.commit(
                EventProposal(
                    event_type=
                        EventType.INTERPRETATION_RECORDED,
                    actor_kind=ActorKind.KIKI,
                    actor_id="kiki",
                    epistemic_class=
                        EpistemicClass.INTERNAL_INTERPRETATION,
                    claim_domain=
                        ClaimDomain.INTERNAL_INTERPRETATION,
                    ancestry=(
                        AncestryEdge(
                            base.event_id,
                            DerivationMode.CONTENT,
                        ),
                    ),
                    renderer_mediated=True,
                    renderer_id="unknown-renderer",
                    payload={"claim": "x"},
                )
            )
        self.assertIn(
            GateFailure.RENDERER_UNKNOWN,
            cm.exception.decision.failures,
        )

        self.register_renderer()
        event = self.commit(
            EventProposal(
                event_type=EventType.INTERPRETATION_RECORDED,
                actor_kind=ActorKind.KIKI,
                actor_id="kiki",
                epistemic_class=
                    EpistemicClass.INTERNAL_INTERPRETATION,
                claim_domain=
                    ClaimDomain.INTERNAL_INTERPRETATION,
                ancestry=(
                    AncestryEdge(
                        base.event_id,
                        DerivationMode.CONTENT,
                    ),
                ),
                renderer_mediated=True,
                renderer_id="renderer-A",
                payload={"claim": "x"},
            )
        )
        self.assertEqual(event.renderer_id, "renderer-A")

    def test_direct_activation_write_is_forbidden(self):
        with self.assertRaises(GateRejected) as cm:
            self.commit(
                EventProposal(
                    event_type=EventType.ACTIVATION_SET,
                    actor_kind=ActorKind.KIKI,
                    actor_id="kiki",
                    epistemic_class=
                        EpistemicClass.INTERNAL_INTERPRETATION,
                    claim_domain=
                        ClaimDomain.INTERNAL_INTERPRETATION,
                    payload={
                        "representation_id": "x",
                        "value": 0.9,
                    },
                )
            )
        self.assertIn(
            GateFailure.ACTIVATION_DIRECT_WRITE_FORBIDDEN,
            cm.exception.decision.failures,
        )

    def test_activation_projector_respects_function_version(self):
        base = self.evidence()

        for version in (
            "count-activation-v1",
            "count-activation-v1",
            "count-activation-v2",
        ):
            self.commit(
                EventProposal(
                    event_type=EventType.ENCOUNTER_RECORDED,
                    actor_kind=ActorKind.KIKI,
                    actor_id="kiki",
                    epistemic_class=
                        EpistemicClass.INTERNAL_INTERPRETATION,
                    claim_domain=
                        ClaimDomain.INTERNAL_INTERPRETATION,
                    ancestry=(
                        AncestryEdge(
                            base.event_id,
                            DerivationMode.CAUSAL_PARENT,
                        ),
                    ),
                    causal_parent_ids=(base.event_id,),
                    payload={
                        "representation_id": base.event_id,
                        "encounter_type": "retrieval",
                        "mode": "design_history",
                        "activation_function_version": version,
                    },
                )
            )

        values = {
            (v.representation_id, v.mode): v.value
            for v in CountActivationV1().project(
                self.ledger.iter_events()
            )
        }
        self.assertEqual(
            values[(base.event_id, "design_history")],
            2.0,
        )

    def test_encounter_requires_activation_version(self):
        base = self.evidence()
        with self.assertRaises(GateRejected) as cm:
            self.commit(
                EventProposal(
                    event_type=EventType.ENCOUNTER_RECORDED,
                    actor_kind=ActorKind.KIKI,
                    actor_id="kiki",
                    epistemic_class=
                        EpistemicClass.INTERNAL_INTERPRETATION,
                    claim_domain=
                        ClaimDomain.INTERNAL_INTERPRETATION,
                    ancestry=(
                        AncestryEdge(
                            base.event_id,
                            DerivationMode.CAUSAL_PARENT,
                        ),
                    ),
                    causal_parent_ids=(base.event_id,),
                    payload={
                        "representation_id": base.event_id,
                        "encounter_type": "retrieval",
                        "mode": "design_history",
                    },
                )
            )
        self.assertIn(
            GateFailure.ACCOUNTING_ENTRY_MISSING,
            cm.exception.decision.failures,
        )

    def test_initial_lease_must_expire_in_future(self):
        with self.assertRaises(GateRejected) as cm:
            self.grant_operator(
                expires_at=(
                    self.now - timedelta(minutes=1)
                ).isoformat()
            )
        self.assertIn(
            GateFailure.OPERATOR_LEASE_EXPIRY_INVALID,
            cm.exception.decision.failures,
        )

    def test_expired_lease_can_be_recovered_by_same_operator(self):
        initial = self.grant_operator(
            expires_at=(
                self.now + timedelta(minutes=10)
            ).isoformat()
        )

        self.now = self.now + timedelta(minutes=20)

        recovered = self.renew_operator(
            initial.event_id,
            expires_at=(
                self.now + timedelta(hours=12)
            ).isoformat(),
        )

        self.assertEqual(
            recovered.event_type,
            EventType.OPERATOR_LEASE_RENEWED,
        )
        self.assertEqual(
            recovered.payload["previous_lease_event_id"],
            initial.event_id,
        )

    def test_lease_recovery_must_name_latest_lease(self):
        initial = self.grant_operator()
        renewal = self.renew_operator(initial.event_id)

        self.now = self.now + timedelta(hours=13)

        with self.assertRaises(GateRejected) as cm:
            self.renew_operator(
                initial.event_id,
                expires_at=(
                    self.now + timedelta(hours=12)
                ).isoformat(),
            )
        self.assertIn(
            GateFailure.TRANSITION_NOT_AUTHORIZED,
            cm.exception.decision.failures,
        )

    def test_canonical_endorsement_requires_live_operator(self):
        lease = self.grant_operator()

        proposal = self.commit(
            EventProposal(
                event_type=
                    EventType.CANONICAL_ENDORSEMENT_PROPOSED,
                actor_kind=ActorKind.KIKI,
                actor_id="kiki",
                epistemic_class=EpistemicClass.GOVERNANCE,
                claim_domain=ClaimDomain.GOVERNANCE,
                payload={"target": "next"},
            )
        )

        authorized = self.commit(
            EventProposal(
                event_type=
                    EventType.CANONICAL_ENDORSEMENT_AUTHORIZED,
                actor_kind=ActorKind.OPERATOR,
                actor_id="operator-1",
                epistemic_class=EpistemicClass.GOVERNANCE,
                claim_domain=ClaimDomain.GOVERNANCE,
                causal_parent_ids=(proposal.event_id,),
                payload={
                    "proposal_event_id": proposal.event_id,
                    "target": "next",
                },
            )
        )
        self.assertEqual(
            authorized.event_type,
            EventType.CANONICAL_ENDORSEMENT_AUTHORIZED,
        )

        self.now = self.now + timedelta(hours=13)
        proposal2 = self.commit(
            EventProposal(
                event_type=
                    EventType.CANONICAL_ENDORSEMENT_PROPOSED,
                actor_kind=ActorKind.KIKI,
                actor_id="kiki",
                epistemic_class=EpistemicClass.GOVERNANCE,
                claim_domain=ClaimDomain.GOVERNANCE,
                payload={"target": "later"},
            )
        )
        with self.assertRaises(GateRejected) as cm:
            self.commit(
                EventProposal(
                    event_type=
                        EventType.CANONICAL_ENDORSEMENT_AUTHORIZED,
                    actor_kind=ActorKind.OPERATOR,
                    actor_id="operator-1",
                    epistemic_class=EpistemicClass.GOVERNANCE,
                    claim_domain=ClaimDomain.GOVERNANCE,
                    causal_parent_ids=(proposal2.event_id,),
                    payload={
                        "proposal_event_id":
                            proposal2.event_id,
                    },
                )
            )
        self.assertIn(
            GateFailure.OPERATOR_LEASE_EXPIRED,
            cm.exception.decision.failures,
        )

    def test_gate_cannot_be_supplied_per_commit(self):
        class AllowEverything:
            def validate(self, proposal, ledger):
                return GateDecision.allow()

        proposal = EventProposal(
            event_type=EventType.ACTIVATION_SET,
            actor_kind=ActorKind.KIKI,
            actor_id="kiki",
            epistemic_class=
                EpistemicClass.INTERNAL_INTERPRETATION,
            claim_domain=ClaimDomain.INTERNAL_INTERPRETATION,
            payload={"value": 1.0},
        )

        with self.assertRaises(TypeError):
            self.ledger.commit(proposal, AllowEverything())

    def test_event_id_retry_is_crash_idempotent(self):
        proposal = EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM,
            actor_id="importer",
            epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT,
            payload={"x": 1},
        )

        first = self.commit(
            proposal,
            event_id="fixed-id-001",
        )
        retry = self.commit(
            proposal,
            event_id="fixed-id-001",
        )

        self.assertEqual(first.event_id, retry.event_id)
        self.assertEqual(
            len(list(self.ledger.iter_events())),
            1,
        )

    def test_event_id_collision_with_different_proposal_conflicts(self):
        first = EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM,
            actor_id="importer",
            epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT,
            payload={"x": 1},
        )
        second = EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM,
            actor_id="importer",
            epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT,
            payload={"x": 2},
        )

        self.commit(first, event_id="fixed-id-001")
        with self.assertRaises(IdempotencyConflict):
            self.commit(second, event_id="fixed-id-001")

    def test_idempotency_key_collision_still_conflicts(self):
        first = EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM,
            actor_id="importer",
            epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT,
            payload={"x": 1},
            idempotency_key="same-key",
        )
        second = EventProposal(
            event_type=EventType.EVIDENCE_INGESTED,
            actor_kind=ActorKind.SYSTEM,
            actor_id="importer",
            epistemic_class=EpistemicClass.SOURCE_EVIDENCE,
            claim_domain=ClaimDomain.EXTERNAL_FACT,
            payload={"x": 2},
            idempotency_key="same-key",
        )

        self.commit(first)
        with self.assertRaises(IdempotencyConflict):
            self.commit(second)

    def test_unknown_housekeeping_table_is_rejected_on_open(self):
        self.evidence()
        conn = sqlite3.connect(self.db)
        conn.execute(
            "CREATE TABLE sneaky_cache (id INTEGER PRIMARY KEY)"
        )
        conn.commit()
        conn.close()

        with self.assertRaises(IntegrityError):
            EventLedger(
                self.db,
                now_fn=lambda: self.now,
            )

    def test_raw_sql_forged_insert_is_detected_on_open(self):
        self.evidence()

        conn = sqlite3.connect(self.db)
        conn.execute(
            """
            INSERT INTO canonical_events(
                event_id,
                committed_at,
                event_type,
                actor_kind,
                actor_id,
                epistemic_class,
                claim_domain,
                payload_json,
                ancestry_json,
                causal_parent_ids_json,
                content_restrictions_json,
                renderer_mediated,
                renderer_id,
                policy_version,
                idempotency_key,
                proposal_hash,
                prev_event_hash,
                event_hash
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "forged",
                self.now.isoformat(),
                EventType.EVIDENCE_INGESTED.value,
                ActorKind.SYSTEM.value,
                "raw-sql",
                EpistemicClass.SOURCE_EVIDENCE.value,
                ClaimDomain.EXTERNAL_FACT.value,
                "{}",
                "[]",
                "[]",
                "[]",
                0,
                None,
                "kiki-mind-v0.2.2",
                None,
                "garbage-proposal-hash",
                "garbage-prev-hash",
                "garbage-event-hash",
            ),
        )
        conn.commit()
        conn.close()

        with self.assertRaises(IntegrityError):
            EventLedger(
                self.db,
                now_fn=lambda: self.now,
            )

    def test_causal_ancestry_and_parent_lists_must_agree(self):
        base = self.evidence()

        with self.assertRaises(GateRejected) as cm:
            self.commit(
                EventProposal(
                    event_type=EventType.ENCOUNTER_RECORDED,
                    actor_kind=ActorKind.KIKI,
                    actor_id="kiki",
                    epistemic_class=
                        EpistemicClass.INTERNAL_INTERPRETATION,
                    claim_domain=
                        ClaimDomain.INTERNAL_INTERPRETATION,
                    ancestry=(
                        AncestryEdge(
                            base.event_id,
                            DerivationMode.CAUSAL_PARENT,
                        ),
                    ),
                    causal_parent_ids=(),
                    payload={
                        "representation_id": base.event_id,
                        "encounter_type": "retrieval",
                        "mode": "design_history",
                        "activation_function_version":
                            "count-activation-v1",
                    },
                )
            )

        self.assertIn(
            GateFailure.CAUSAL_ORDER_INVALID,
            cm.exception.decision.failures,
        )


    def test_raw_sql_forged_insert_blocks_next_commit(self):
        self.evidence()

        conn = sqlite3.connect(self.db)
        conn.execute(
            """
            INSERT INTO canonical_events(
                event_id,
                committed_at,
                event_type,
                actor_kind,
                actor_id,
                epistemic_class,
                claim_domain,
                payload_json,
                ancestry_json,
                causal_parent_ids_json,
                content_restrictions_json,
                renderer_mediated,
                renderer_id,
                policy_version,
                idempotency_key,
                proposal_hash,
                prev_event_hash,
                event_hash
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "forged-tail",
                self.now.isoformat(),
                EventType.EVIDENCE_INGESTED.value,
                ActorKind.SYSTEM.value,
                "raw-sql",
                EpistemicClass.SOURCE_EVIDENCE.value,
                ClaimDomain.EXTERNAL_FACT.value,
                "{}",
                "[]",
                "[]",
                "[]",
                0,
                None,
                "kiki-mind-v0.2.2",
                None,
                "garbage-proposal-hash",
                "garbage-prev-hash",
                "garbage-event-hash",
            ),
        )
        conn.commit()
        conn.close()

        with self.assertRaises(IntegrityError):
            self.evidence()

    def test_missing_append_only_trigger_blocks_next_commit(self):
        self.evidence()

        conn = sqlite3.connect(self.db)
        conn.execute(
            "DROP TRIGGER canonical_events_no_update"
        )
        conn.commit()
        conn.close()

        with self.assertRaises(IntegrityError):
            self.evidence()



if __name__ == "__main__":
    unittest.main()
