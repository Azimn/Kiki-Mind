from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from .models import (
    ActorKind,
    ClaimDomain,
    DerivationMode,
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
    """Deterministic structural gate.

    Trust boundary: the gate can enforce consistency of declared ancestry and
    DerivationMode, but it cannot prove that a proposer labeled semantic content
    correctly. Proposal construction remains a trusted-input boundary and is
    intentionally visible in the implementation spec.
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

            # Deliberately allow both active renewal and post-expiry recovery by
            # the same operator identity. This fixes ordinary lease lapse without
            # inventing an operator-succession mechanism.

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

    def _activation(self, p, f, d):
        if p.event_type == EventType.ACTIVATION_SET:
            f.append(GateFailure.ACTIVATION_DIRECT_WRITE_FORBIDDEN)
            d.append(
                "activation is derived only from committed encounters plus "
                "a versioned function"
            )
