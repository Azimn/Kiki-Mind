"""Kiki Mind's typed vocabulary.

These types are the labels sewn into the architecture. They keep evidence,
interpretation, autobiography, governance, renderers, and reconstruction from
ending up in one giant mystery handbag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ActorKind(str, Enum):
    SYSTEM = "system"
    KIKI = "kiki"
    OPERATOR = "operator"
    RENDERER = "renderer"
    MIGRATION = "migration"
    TEST = "test"


class EventType(str, Enum):
    EVIDENCE_INGESTED = "evidence.ingested"
    RECONSTRUCTION_DECLARED = "reconstruction.declared"
    RENDERER_REGISTERED = "renderer.registered"
    INTERPRETATION_RECORDED = "interpretation.recorded"
    ENCOUNTER_RECORDED = "encounter.recorded"
    NEGATIVE_SPACE_RECORDED = "negative_space.recorded"
    DEVELOPMENTAL_OBSERVATION_RECORDED = "developmental.observation.recorded"
    OPERATOR_LEASE_GRANTED = "governance.operator_lease.granted"
    OPERATOR_LEASE_RENEWED = "governance.operator_lease.renewed"
    CANONICAL_ENDORSEMENT_PROPOSED = "lineage.canonical_endorsement.proposed"
    CANONICAL_ENDORSEMENT_AUTHORIZED = "lineage.canonical_endorsement.authorized"
    ACTIVATION_SET = "activation.set"


class DevelopmentalObservationKind(str, Enum):
    SELF_REPORT = "self_report"
    CHOICE = "choice"
    COMMITMENT = "commitment"
    CORRECTION = "correction"


class DevelopmentalContextProvenance(str, Enum):
    RUNTIME_SUPPLIED = "runtime_supplied"
    OPERATOR_SUPPLIED = "operator_supplied"
    RENDERER_DECLARED = "renderer_declared"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class EpistemicClass(str, Enum):
    SOURCE_EVIDENCE = "source_evidence"
    AUTHORED_IDENTITY = "authored_identity"
    HISTORICAL_INTERACTION = "historical_interaction"
    SYNTHETIC_DESIGN = "synthetic_design"
    DECLARED_RECONSTRUCTION = "declared_reconstruction"
    INTERNAL_INTERPRETATION = "internal_interpretation"
    AUTOBIOGRAPHICAL_EPISODE = "autobiographical_episode"
    DERIVED_RESIDUE = "derived_residue"
    GOVERNANCE = "governance"
    RENDERER_METADATA = "renderer_metadata"
    DEVELOPMENTAL_OBSERVATION = "developmental_observation"


class ClaimDomain(str, Enum):
    EXTERNAL_FACT = "external_fact"
    AUTOBIOGRAPHICAL = "autobiographical"
    DESIGN_HISTORY = "design_history"
    INTERNAL_INTERPRETATION = "internal_interpretation"
    GOVERNANCE = "governance"
    RENDERER_METADATA = "renderer_metadata"
    DEVELOPMENTAL_EVIDENCE = "developmental_evidence"


class Restriction(str, Enum):
    FORBID_AUTOBIOGRAPHY = "forbid_autobiography"
    FORBID_CANONICAL_EXPERIENCE = "forbid_canonical_experience"
    FORBID_EXTERNAL_FACT = "forbid_external_fact"


class DerivationMode(str, Enum):
    CONTENT = "content"
    PROVENANCE_REFERENCE = "provenance_reference"
    CAUSAL_PARENT = "causal_parent"


@dataclass(frozen=True)
class AncestryEdge:
    event_id: str
    mode: DerivationMode


@dataclass(frozen=True)
class EventProposal:
    event_type: EventType
    actor_kind: ActorKind
    actor_id: str
    epistemic_class: EpistemicClass
    claim_domain: ClaimDomain
    payload: Mapping[str, Any] = field(default_factory=dict)
    ancestry: Sequence[AncestryEdge] = field(default_factory=tuple)
    causal_parent_ids: Sequence[str] = field(default_factory=tuple)
    content_restrictions: frozenset[Restriction] = field(default_factory=frozenset)
    renderer_mediated: bool = False
    renderer_id: str | None = None
    policy_version: str = "kiki-mind-v0.3.0"
    idempotency_key: str | None = None


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    sequence: int
    committed_at: str
    event_type: EventType
    actor_kind: ActorKind
    actor_id: str
    epistemic_class: EpistemicClass
    claim_domain: ClaimDomain
    payload: Mapping[str, Any]
    ancestry: tuple[AncestryEdge, ...]
    causal_parent_ids: tuple[str, ...]
    content_restrictions: frozenset[Restriction]
    renderer_mediated: bool
    renderer_id: str | None
    policy_version: str
    idempotency_key: str | None
    prev_event_hash: str
    event_hash: str
