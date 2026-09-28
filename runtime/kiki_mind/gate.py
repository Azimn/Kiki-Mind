"""The Transition Gate, or: the velvet rope around canonical history.

Being charming is not authorization. Being plausible is not provenance.
Proposals get in only when the declared structure satisfies the constitution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from .models import (
    ActorKind,
    ClaimDomain,
    DerivationMode,
    DevelopmentalContextProvenance,
    DevelopmentalObservationKind,
    EpistemicClass,
    EventProposal,
    EventRecord,
    EventType,
    Restriction,
)


class GateFailure(str, Enum):
    SCHEMA_INVALID = "schema_invalid"
    UNKNOWN_ANCESTOR = "unknown_ancestor"
    PROVENANCE_NOT_CONSERVED = "provenance_not_conserved"
    TAINT_CLOSURE_VIOLATION = "taint_closure_violation"
    CLAIM_DOMAIN_RESTRICTED = "claim_domain_restricted"
    ACTOR_NOT_AUTHORIZED = "actor_not_authorized"
    TRANSITION_NOT_AUTHORIZED = "transition_not_authorized"
    LINEAGE_AUTHORITY_MISSING = "lineage_authority_missing"
    EPISTEMIC_CLASS_INCOMPATIBLE = "epistemic_class_incompatible"
    CAUSAL_ORDER_INVALID = "causal_order_invalid"
    RENDERER_ATTRIBUTION_MISSING = "renderer_attribution_missing"
    RENDERER_UNKNOWN = "renderer_unknown"
    ACCOUNTING_ENTRY_MISSING = "accounting_entry_missing"
    ACTIVATION_DIRECT_WRITE_FORBIDDEN = "activation_direct_write_forbidden"
    OPERATOR_LEASE_MISSING = "operator_lease_missing"
    OPERATOR_LEASE_EXPIRED = "operator_lease_expired"
    OPERATOR_LEASE_EXPIRY_INVALID = "operator_lease_expiry_invalid"
    ENDORSEMENT_PROPOSAL_MISSING = "endorsement_proposal_missing"
    DEVELOPMENTAL_OBSERVATION_INVALID = "developmental_observation_invalid"


@dataclass(frozen=True)
class GateDecision:
    accepted: bool
    failures: tuple[GateFailure, ...] = ()
    details: tuple[str, ...] = ()

    @classmethod
    def allow(cls) -> "GateDecision":
        return cls(True, (), ())

    @classmethod
    def deny(cls, failures, details) -> "GateDecision":
        return cls(False, tuple(failures), tuple(details))


class LedgerView(Protocol):
    def get_event(self, event_id: str) -> EventRecord | None: ...
    def renderer_exists(self, renderer_id: str) -> bool: ...
    def operator_lease_status(
        self, operator_id: str, at: datetime
    ) -> tuple[str, EventRecord | None]: ...
    def endorsement_proposal_exists(self, proposal_event_id: str) -> bool: ...
    def has_any_operator_lease(self) -> bool: ...
    def developmental_commitment_root_exists(
        self, commitment_id: str
    ) -> bool: ...
    def developmental_commitment_child_exists(
        self, prior_event_id: str
    ) -> bool: ...


def _parse_expiry(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TransitionGate:
    """Deterministic structural gate with a very strict guest list.

    The gate enforces declared ancestry, authority, taint, accounting, and
    transition structure. It does not pretend to read minds or prove semantic
    truth. Proposal construction remains a trusted-input boundary, because fake
    certainty in a sequined dress is still fake certainty.
    """

    DERIVED_CLASSES = {
        EpistemicClass.INTERNAL_INTERPRETATION,
        EpistemicClass.AUTOBIOGRAPHICAL_EPISODE,
        EpistemicClass.DERIVED_RESIDUE,
    }

    def __init__(self, now_fn=None):
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def validate(self, p: EventProposal, ledger: LedgerView) -> GateDecision:
        failures: list[GateFailure] = []
        details: list[str] = []

        self._schema(p, failures, details)
        ancestors = self._ancestry(p, ledger, failures, details)
        parents = self._parents(p, ledger, failures, details)

        self._provenance(p, ancestors, failures, details)
        self._taint(p, ancestors, failures, details)
        self._claim_domain(p, failures, details)
        self._actors(p, ledger, failures, details)
        self._transition_auth(p, ledger, failures, details)
        self._lineage(p, ledger, failures, details)
        self._epistemic(p, failures, details)
        self._causal(p, parents, failures, details)
        self._renderer(p, ledger, failures, details)
        self._accounting(p, failures, details)
        self._developmental(p, ledger, failures, details)
        self._activation(p, failures, details)

        return GateDecision.deny(failures, details) if failures else GateDecision.allow()

    def _schema(self, p, f, d):
        if not p.actor_id or not p.actor_id.strip():
            f.append(GateFailure.SCHEMA_INVALID)
            d.append("actor_id must be non-empty")
        if not p.policy_version or not p.policy_version.strip():
            f.append(GateFailure.SCHEMA_INVALID)
            d.append("policy_version must be non-empty")
        if p.renderer_mediated and not p.renderer_id:
            f.append(GateFailure.RENDERER_ATTRIBUTION_MISSING)
            d.append("renderer-mediated events require renderer_id")

    def _ancestry(self, p, ledger, f, d):
        found, seen = [], set()
        for edge in p.ancestry:
            if edge.event_id in seen:
                f.append(GateFailure.SCHEMA_INVALID)
                d.append(f"duplicate ancestry edge: {edge.event_id}")
                continue
            seen.add(edge.event_id)
            record = ledger.get_event(edge.event_id)
            if record is None:
                f.append(GateFailure.UNKNOWN_ANCESTOR)
                d.append(f"unknown ancestry event: {edge.event_id}")
            else:
                found.append((edge, record))
        return found

    def _parents(self, p, ledger, f, d):
        found, seen = [], set()
        for event_id in p.causal_parent_ids:
            if event_id in seen:
                f.append(GateFailure.SCHEMA_INVALID)
                d.append(f"duplicate causal parent: {event_id}")
                continue
            seen.add(event_id)
            record = ledger.get_event(event_id)
            if record is None:
                f.append(GateFailure.CAUSAL_ORDER_INVALID)
                d.append(f"unknown causal parent: {event_id}")
            else:
                found.append(record)
        return found

    def _provenance(self, p, ancestors, f, d):
        if p.epistemic_class in self.DERIVED_CLASSES and not ancestors:
            f.append(GateFailure.PROVENANCE_NOT_CONSERVED)
            d.append("derived artifacts require ancestry or explicit reconstruction")

    def _taint(self, p, ancestors, f, d):
        inherited = set()
        for edge, record in ancestors:
            if edge.mode == DerivationMode.CONTENT:
                inherited.update(record.content_restrictions)
        missing = inherited.difference(p.content_restrictions)
        if missing:
            f.append(GateFailure.TAINT_CLOSURE_VIOLATION)
            d.append(
                "content-derived artifact dropped restrictions: "
                + ", ".join(sorted(x.value for x in missing))
            )

    def _claim_domain(self, p, f, d):
        if (
            p.claim_domain == ClaimDomain.AUTOBIOGRAPHICAL
            and Restriction.FORBID_AUTOBIOGRAPHY in p.content_restrictions
        ):
            f.append(GateFailure.CLAIM_DOMAIN_RESTRICTED)
            d.append("content restrictions forbid autobiographical use")
        if (
            p.claim_domain == ClaimDomain.EXTERNAL_FACT
            and Restriction.FORBID_EXTERNAL_FACT in p.content_restrictions
        ):
            f.append(GateFailure.CLAIM_DOMAIN_RESTRICTED)
            d.append("content restrictions forbid external-fact use")

    def _actors(self, p, ledger, f, d):
        if (
            p.event_type == EventType.RENDERER_REGISTERED
            and p.actor_kind not in {ActorKind.SYSTEM, ActorKind.OPERATOR}
        ):
            f.append(GateFailure.ACTOR_NOT_AUTHORIZED)
            d.append("renderer registration requires system or operator")

        if (
            p.event_type == EventType.DEVELOPMENTAL_OBSERVATION_RECORDED
            and p.actor_kind != ActorKind.KIKI
        ):
            f.append(GateFailure.ACTOR_NOT_AUTHORIZED)
            d.append("developmental observations must originate from Kiki")

        if (
            p.event_type == EventType.CANONICAL_ENDORSEMENT_PROPOSED
            and p.actor_kind != ActorKind.KIKI
        ):
            f.append(GateFailure.ACTOR_NOT_AUTHORIZED)
            d.append("canonical endorsement proposal must originate from Kiki")

        if (
            p.event_type == EventType.CANONICAL_ENDORSEMENT_AUTHORIZED
            and p.actor_kind != ActorKind.OPERATOR
        ):
            f.append(GateFailure.ACTOR_NOT_AUTHORIZED)
            d.append("canonical endorsement authorization requires operator")

        if p.event_type == EventType.OPERATOR_LEASE_GRANTED:
            if ledger.has_any_operator_lease():
                f.append(GateFailure.ACTOR_NOT_AUTHORIZED)
                d.append("operator lease already exists; use renewal/succession")
            elif p.actor_kind != ActorKind.SYSTEM:
                f.append(GateFailure.ACTOR_NOT_AUTHORIZED)
                d.append("initial operator lease requires system bootstrap")

        if (
            p.event_type == EventType.OPERATOR_LEASE_RENEWED
            and p.actor_kind != ActorKind.OPERATOR
        ):
            f.append(GateFailure.ACTOR_NOT_AUTHORIZED)
            d.append("operator lease renewal requires operator actor")

    def _transition_auth(self, p, ledger, f, d):
        if p.event_type not in {
            EventType.OPERATOR_LEASE_GRANTED,
            EventType.OPERATOR_LEASE_RENEWED,
        }:
            return

        now = self._now_fn()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now = now.astimezone(timezone.utc)

        expiry = _parse_expiry(p.payload.get("expires_at"))
        if expiry is None or expiry <= now:
            f.append(GateFailure.OPERATOR_LEASE_EXPIRY_INVALID)
            d.append("new operator lease expiry must be a valid future timestamp")
            return

        operator_id = p.payload.get("operator_id")
        if p.event_type == EventType.OPERATOR_LEASE_RENEWED:
            if operator_id != p.actor_id:
                f.append(GateFailure.TRANSITION_NOT_AUTHORIZED)
                d.append("operator lease renewal actor_id must match payload operator_id")
                return

            status, previous = ledger.operator_lease_status(p.actor_id, now)
            if status == "missing" or previous is None:
                f.append(GateFailure.OPERATOR_LEASE_MISSING)
                d.append("operator cannot renew without a prior lease")
                return

            previous_id = p.payload.get("previous_lease_event_id")
            if previous_id != previous.event_id:
                f.append(GateFailure.TRANSITION_NOT_AUTHORIZED)
                d.append("lease renewal must name the latest prior lease event")

            # Same operator, same velvet wristband. We allow active renewal and
            # post-expiry recovery without quietly inventing succession semantics.

    def _lineage(self, p, ledger, f, d):
        if p.event_type != EventType.CANONICAL_ENDORSEMENT_AUTHORIZED:
            return

        status, _ = ledger.operator_lease_status(p.actor_id, self._now_fn())
        if status != "active":
            f.append(
                GateFailure.OPERATOR_LEASE_EXPIRED
                if status == "expired"
                else GateFailure.OPERATOR_LEASE_MISSING
            )
            d.append("canonical endorsement requires live operator lease")

        proposal_id = p.payload.get("proposal_event_id")
        if not isinstance(proposal_id, str) or not proposal_id:
            f.append(GateFailure.ENDORSEMENT_PROPOSAL_MISSING)
            d.append("authorization requires proposal_event_id")
        elif not ledger.endorsement_proposal_exists(proposal_id):
            f.append(GateFailure.ENDORSEMENT_PROPOSAL_MISSING)
            d.append("referenced endorsement proposal does not exist")
        elif proposal_id not in p.causal_parent_ids:
            f.append(GateFailure.TRANSITION_NOT_AUTHORIZED)
            d.append("endorsement proposal must be a causal parent")

    def _epistemic(self, p, f, d):
        allowed = {
            EventType.EVIDENCE_INGESTED: {
                EpistemicClass.SOURCE_EVIDENCE,
                EpistemicClass.AUTHORED_IDENTITY,
                EpistemicClass.HISTORICAL_INTERACTION,
                EpistemicClass.SYNTHETIC_DESIGN,
            },
            EventType.RECONSTRUCTION_DECLARED: {
                EpistemicClass.DECLARED_RECONSTRUCTION,
            },
            EventType.RENDERER_REGISTERED: {
                EpistemicClass.RENDERER_METADATA,
            },
            EventType.INTERPRETATION_RECORDED: {
                EpistemicClass.INTERNAL_INTERPRETATION,
                EpistemicClass.DERIVED_RESIDUE,
            },
            EventType.ENCOUNTER_RECORDED: {
                EpistemicClass.INTERNAL_INTERPRETATION,
            },
            EventType.NEGATIVE_SPACE_RECORDED: {
                EpistemicClass.INTERNAL_INTERPRETATION,
                EpistemicClass.GOVERNANCE,
            },
            EventType.DEVELOPMENTAL_OBSERVATION_RECORDED: {
                EpistemicClass.DEVELOPMENTAL_OBSERVATION,
            },
            EventType.OPERATOR_LEASE_GRANTED: {
                EpistemicClass.GOVERNANCE,
            },
            EventType.OPERATOR_LEASE_RENEWED: {
                EpistemicClass.GOVERNANCE,
            },
            EventType.CANONICAL_ENDORSEMENT_PROPOSED: {
                EpistemicClass.GOVERNANCE,
            },
            EventType.CANONICAL_ENDORSEMENT_AUTHORIZED: {
                EpistemicClass.GOVERNANCE,
            },
        }
        expected = allowed.get(p.event_type)
        if expected is not None and p.epistemic_class not in expected:
            f.append(GateFailure.EPISTEMIC_CLASS_INCOMPATIBLE)
            d.append(f"{p.event_type.value} incompatible with {p.epistemic_class.value}")

    def _causal(self, p, parents, f, d):
        ids = set(p.causal_parent_ids)
        for edge in p.ancestry:
            if (
                edge.mode == DerivationMode.CAUSAL_PARENT
                and edge.event_id not in ids
            ):
                f.append(GateFailure.CAUSAL_ORDER_INVALID)
                d.append(
                    f"causal ancestry {edge.event_id} missing from causal_parent_ids"
                )

    def _renderer(self, p, ledger, f, d):
        if not p.renderer_mediated:
            if p.actor_kind == ActorKind.RENDERER:
                f.append(GateFailure.RENDERER_ATTRIBUTION_MISSING)
                d.append("renderer actor must set renderer_mediated")
            return

        if not p.renderer_id:
            return

        if p.actor_kind == ActorKind.RENDERER and p.actor_id != p.renderer_id:
            f.append(GateFailure.RENDERER_ATTRIBUTION_MISSING)
            d.append("renderer actor_id must equal renderer_id")

        if not ledger.renderer_exists(p.renderer_id):
            f.append(GateFailure.RENDERER_UNKNOWN)
            d.append(f"renderer not registered: {p.renderer_id}")

    def _accounting(self, p, f, d):
        if p.event_type == EventType.ENCOUNTER_RECORDED:
            required = {
                "representation_id",
                "encounter_type",
                "mode",
                "activation_function_version",
            }
            missing = sorted(x for x in required if x not in p.payload)
            if missing:
                f.append(GateFailure.ACCOUNTING_ENTRY_MISSING)
                d.append("encounter missing: " + ", ".join(missing))

        if (
            p.event_type == EventType.NEGATIVE_SPACE_RECORDED
            and not any(
                k in p.payload
                for k in (
                    "protected_object_id",
                    "cost_description",
                    "aggregate_count",
                )
            )
        ):
            f.append(GateFailure.ACCOUNTING_ENTRY_MISSING)
            d.append(
                "negative-space record needs protection, cost, or aggregate"
            )

        if p.event_type in {
            EventType.OPERATOR_LEASE_GRANTED,
            EventType.OPERATOR_LEASE_RENEWED,
        }:
            if not isinstance(p.payload.get("operator_id"), str):
                f.append(GateFailure.ACCOUNTING_ENTRY_MISSING)
                d.append("operator lease requires operator_id")
            if not isinstance(p.payload.get("expires_at"), str):
                f.append(GateFailure.ACCOUNTING_ENTRY_MISSING)
                d.append("operator lease requires expires_at")

        if p.event_type == EventType.OPERATOR_LEASE_RENEWED:
            if not isinstance(p.payload.get("previous_lease_event_id"), str):
                f.append(GateFailure.ACCOUNTING_ENTRY_MISSING)
                d.append("operator lease renewal requires previous_lease_event_id")

        if (
            p.event_type == EventType.RENDERER_REGISTERED
            and not isinstance(p.payload.get("renderer_id"), str)
        ):
            f.append(GateFailure.ACCOUNTING_ENTRY_MISSING)
            d.append("renderer registration requires renderer_id")

    def _developmental(self, p, ledger, f, d):
        if p.event_type != EventType.DEVELOPMENTAL_OBSERVATION_RECORDED:
            return

        def fail(message):
            f.append(GateFailure.DEVELOPMENTAL_OBSERVATION_INVALID)
            d.append(message)

        if p.claim_domain != ClaimDomain.DEVELOPMENTAL_EVIDENCE:
            fail(
                "developmental observation must use developmental_evidence "
                "claim domain"
            )

        if (
            Restriction.FORBID_CANONICAL_EXPERIENCE
            in p.content_restrictions
        ):
            f.append(GateFailure.CLAIM_DOMAIN_RESTRICTED)
            d.append(
                "content restrictions forbid canonical developmental "
                "observation"
            )

        restricted_parent_ids = []
        for event_id in p.causal_parent_ids:
            parent = ledger.get_event(event_id)
            if (
                parent is not None
                and Restriction.FORBID_CANONICAL_EXPERIENCE
                in parent.content_restrictions
            ):
                restricted_parent_ids.append(event_id)
        if restricted_parent_ids:
            f.append(GateFailure.CLAIM_DOMAIN_RESTRICTED)
            d.append(
                "developmental observation cannot use causal parents "
                "that forbid canonical experience: "
                + ", ".join(sorted(restricted_parent_ids))
            )

        if not p.renderer_mediated or not p.renderer_id:
            fail(
                "developmental observation requires an attributed renderer"
            )

        if not p.causal_parent_ids:
            fail(
                "developmental observation requires canonical causal context"
            )

        causal_ancestry_ids = {
            edge.event_id
            for edge in p.ancestry
            if edge.mode == DerivationMode.CAUSAL_PARENT
        }
        missing_causal_ancestry = set(
            p.causal_parent_ids
        ).difference(causal_ancestry_ids)
        if missing_causal_ancestry:
            fail(
                "developmental causal parents must also appear as "
                "CAUSAL_PARENT ancestry"
            )

        kind_value = p.payload.get("observation_kind")
        try:
            kind = DevelopmentalObservationKind(kind_value)
        except (TypeError, ValueError):
            fail("developmental observation_kind is invalid")
            return

        context = p.payload.get("context")
        if not isinstance(context, dict):
            fail("developmental observation requires context object")
            return

        context_keys = {
            "model_id",
            "provider_id",
            "runtime_id",
            "modality",
            "available_tools",
            "platform_affordances",
            "initiative_possible",
            "refusal_policy_constrained",
            "explicit_user_request",
            "context_provenance",
        }
        actual_context_keys = set(context)
        if actual_context_keys != context_keys:
            fail(
                "developmental context keys must match the v1 contract"
            )
            return

        for key in ("model_id", "provider_id", "runtime_id", "modality"):
            if context[key] is not None and not isinstance(
                context[key], str
            ):
                fail(f"developmental context {key} must be string or null")

        for key in ("available_tools", "platform_affordances"):
            value = context[key]
            if (
                not isinstance(value, list)
                or not all(
                    isinstance(item, str) and item.strip()
                    for item in value
                )
            ):
                fail(
                    f"developmental context {key} must be a list of "
                    "non-empty strings"
                )
            elif len(value) != len(set(value)):
                fail(
                    f"developmental context {key} must not contain "
                    "duplicates"
                )

        for key in (
            "initiative_possible",
            "refusal_policy_constrained",
            "explicit_user_request",
        ):
            if context[key] is not None and not isinstance(
                context[key], bool
            ):
                fail(f"developmental context {key} must be bool or null")

        try:
            DevelopmentalContextProvenance(
                context["context_provenance"]
            )
        except (TypeError, ValueError):
            fail("developmental context provenance is invalid")

        common = {"observation_kind", "context"}
        schemas = {
            DevelopmentalObservationKind.SELF_REPORT: {
                "required": {"report_text"},
                "optional": {
                    "construct_label",
                    "comparison_target_event_id",
                },
            },
            DevelopmentalObservationKind.CHOICE: {
                "required": {
                    "selected_action",
                    "available_actions",
                    "unavailable_actions",
                    "self_initiated",
                },
                "optional": set(),
            },
            DevelopmentalObservationKind.COMMITMENT: {
                "required": {
                    "commitment_id",
                    "phase",
                    "commitment_text",
                    "reminder_supplied",
                    "opportunity_to_act",
                    "prior_commitment_event_id",
                },
                "optional": set(),
            },
            DevelopmentalObservationKind.CORRECTION: {
                "required": {
                    "corrected_event_id",
                    "evidence_event_ids",
                    "correction_text",
                },
                "optional": set(),
            },
        }
        schema = schemas[kind]
        allowed = common | schema["required"] | schema["optional"]
        actual = set(p.payload)

        missing = schema["required"].difference(actual)
        extra = actual.difference(allowed)
        if missing:
            fail(
                "developmental observation missing: "
                + ", ".join(sorted(missing))
            )
        if extra:
            fail(
                "developmental observation has unrecognized fields: "
                + ", ".join(sorted(extra))
            )
        if missing or extra:
            return

        parent_ids = set(p.causal_parent_ids)

        if kind == DevelopmentalObservationKind.SELF_REPORT:
            if (
                not isinstance(p.payload["report_text"], str)
                or not p.payload["report_text"].strip()
            ):
                fail("self-report requires non-empty report_text")
            construct = p.payload.get("construct_label")
            if construct is not None and not isinstance(construct, str):
                fail("construct_label must be string or null")
            comparison = p.payload.get("comparison_target_event_id")
            if comparison is not None:
                if not isinstance(comparison, str):
                    fail(
                        "comparison_target_event_id must be string or null"
                    )
                elif (
                    ledger.get_event(comparison) is None
                    or comparison not in parent_ids
                ):
                    fail(
                        "comparison target must exist and be a causal parent"
                    )

        elif kind == DevelopmentalObservationKind.CHOICE:
            selected = p.payload["selected_action"]
            available = p.payload["available_actions"]
            unavailable = p.payload["unavailable_actions"]
            self_initiated = p.payload["self_initiated"]
            if not isinstance(selected, str) or not selected.strip():
                fail("choice requires non-empty selected_action")
            if (
                not isinstance(available, list)
                or not available
                or not all(
                    isinstance(item, str) and item.strip()
                    for item in available
                )
            ):
                fail(
                    "available_actions must be a non-empty list of "
                    "non-empty strings"
                )
            else:
                if len(available) != len(set(available)):
                    fail("available_actions must not contain duplicates")
                if selected not in available:
                    fail(
                        "selected_action must appear in available_actions"
                    )

            if (
                not isinstance(unavailable, list)
                or not all(
                    isinstance(item, str) and item.strip()
                    for item in unavailable
                )
            ):
                fail(
                    "unavailable_actions must be a list of non-empty "
                    "strings"
                )
            else:
                if len(unavailable) != len(set(unavailable)):
                    fail(
                        "unavailable_actions must not contain duplicates"
                    )
                if set(available).intersection(unavailable):
                    fail(
                        "available_actions and unavailable_actions must "
                        "be disjoint"
                    )
            if (
                self_initiated is not None
                and not isinstance(self_initiated, bool)
            ):
                fail("self_initiated must be bool or null")

        elif kind == DevelopmentalObservationKind.COMMITMENT:
            commitment_id = p.payload["commitment_id"]
            phase = p.payload["phase"]
            prior_id = p.payload["prior_commitment_event_id"]
            if (
                not isinstance(commitment_id, str)
                or not commitment_id.strip()
            ):
                fail("commitment requires non-empty commitment_id")
            if (
                not isinstance(p.payload["commitment_text"], str)
                or not p.payload["commitment_text"].strip()
            ):
                fail("commitment requires non-empty commitment_text")
            allowed_phases = {
                "made",
                "revised",
                "fulfilled",
                "declined",
                "expired_unresolved",
            }
            if phase not in allowed_phases:
                fail("commitment phase is invalid")
            for key in ("reminder_supplied", "opportunity_to_act"):
                value = p.payload[key]
                if value is not None and not isinstance(value, bool):
                    fail(f"{key} must be bool or null")

            if phase == "made":
                if prior_id is not None:
                    fail(
                        "new commitment must not claim a prior commitment"
                    )
                if (
                    isinstance(commitment_id, str)
                    and commitment_id.strip()
                    and ledger.developmental_commitment_root_exists(
                        commitment_id
                    )
                ):
                    fail(
                        "commitment_id already has a made root; use a new "
                        "commitment_id for a new lifecycle"
                    )
            else:
                if not isinstance(prior_id, str):
                    fail(
                        "non-initial commitment phase requires prior event"
                    )
                else:
                    prior = ledger.get_event(prior_id)
                    if prior is None or prior_id not in parent_ids:
                        fail(
                            "prior commitment must exist and be a causal "
                            "parent"
                        )
                    elif (
                        prior.event_type
                        != EventType.DEVELOPMENTAL_OBSERVATION_RECORDED
                        or prior.payload.get("observation_kind")
                        != DevelopmentalObservationKind.COMMITMENT.value
                        or prior.payload.get("commitment_id")
                        != commitment_id
                    ):
                        fail(
                            "prior commitment must belong to the same "
                            "commitment lineage"
                        )
                    else:
                        prior_phase = prior.payload.get("phase")
                        allowed_transitions = {
                            "made": {
                                "revised",
                                "fulfilled",
                                "declined",
                                "expired_unresolved",
                            },
                            "revised": {
                                "revised",
                                "fulfilled",
                                "declined",
                                "expired_unresolved",
                            },
                        }
                        if phase not in allowed_transitions.get(
                            prior_phase,
                            set(),
                        ):
                            fail(
                                "commitment phase transition is invalid: "
                                f"{prior_phase} -> {phase}"
                            )
                        if (
                            ledger.developmental_commitment_child_exists(
                                prior_id
                            )
                        ):
                            fail(
                                "commitment lineage already has a child "
                                "for the named prior event"
                            )

        elif kind == DevelopmentalObservationKind.CORRECTION:
            corrected_id = p.payload["corrected_event_id"]
            evidence_ids = p.payload["evidence_event_ids"]
            if (
                not isinstance(corrected_id, str)
                or ledger.get_event(corrected_id) is None
                or corrected_id not in parent_ids
            ):
                fail(
                    "corrected_event_id must exist and be a causal parent"
                )
            if (
                not isinstance(evidence_ids, list)
                or not evidence_ids
                or not all(isinstance(item, str) for item in evidence_ids)
            ):
                fail("evidence_event_ids must be a non-empty string list")
            else:
                for event_id in evidence_ids:
                    if (
                        ledger.get_event(event_id) is None
                        or event_id not in parent_ids
                    ):
                        fail(
                            "each correction evidence event must exist and "
                            "be a causal parent"
                        )
            if (
                not isinstance(p.payload["correction_text"], str)
                or not p.payload["correction_text"].strip()
            ):
                fail("correction requires non-empty correction_text")

    def _activation(self, p, f, d):
        if p.event_type == EventType.ACTIVATION_SET:
            f.append(GateFailure.ACTIVATION_DIRECT_WRITE_FORBIDDEN)
            d.append(
                "activation is derived only from committed encounters plus "
                "a versioned function"
            )
