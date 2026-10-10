"""Kiki's canonical event receipts as read-only cognition candidates.

Optional adapter for the shared MemoryCognitionPort defined by
Azimn/Pretorius-Connectome. It does not import that project's memories,
copy Kiki's event ledger, write projections or promote source evidence into
Kiki's lived autobiography. It exposes fixed event metadata only, never
free-form payload content, private messages or self-report text.

The host must supply an already authenticated, verified EventLedger; the
shared port's in-process capability is NOT end-user authentication.
"""
from __future__ import annotations

from hashlib import sha256
import re

from pretorius_connectome.cognition_port import (
    MemoryCandidate, MemorySourceMismatch, SourceDescriptor,
)

from .ledger import EventLedger
from .models import (
    ActorKind, ClaimDomain, DevelopmentalObservationKind,
    EpistemicClass, EventType,
)

NAMESPACE = "kiki.canonical.events"
VERSION = "kiki-ledger-metadata-v0.1"
ENCODER = "canonical-event-metadata-tokens-v1"
GENESIS_DIGEST = sha256(b"kiki-canonical-ledger-genesis-v1").hexdigest()
TOKENS = re.compile(r"[a-z0-9]+")

_OBSERVATIONS = frozenset(x.value for x in DevelopmentalObservationKind)
_ENCOUNTERS = frozenset(("retrieval", "interaction", "conversation", "rehearsal"))
_ALIASES = {
    EventType.EVIDENCE_INGESTED: ("source evidence ingested", "external_document"),
    EventType.INTERPRETATION_RECORDED: ("internal interpretation recorded", "uncertain"),
    EventType.ENCOUNTER_RECORDED: ("encounter recorded", "observed_runtime"),
    EventType.DEVELOPMENTAL_OBSERVATION_RECORDED: (
        "developmental observation recorded", "observed_runtime"
    ),
}


class StaleLedgerProjection(MemorySourceMismatch):
    """The canonical ledger advanced since this disposable snapshot."""


class KikiLedgerCognitionSource:
    """Temporary, metadata-only index of a hash-verified canonical prefix.

    Retrieval results report the EXISTENCE of ledger receipts, not that the
    contents of a source, a renderer's report or a psychological trait are true.

    Explicit no-content rule: neither event.payload free text nor ancestry
    texts enter search or CognitionEvidence. All index text is formed from
    fixed enum names and allowlisted enum-like non-private tags. A consumer
    wanting episode content needs a separately reviewed visibility contract.
    """

    def __init__(self, ledger: EventLedger):
        if not isinstance(ledger, EventLedger):
            raise TypeError("KikiLedgerCognitionSource requires an EventLedger")
        self._ledger = ledger
        ledger.verify_integrity()
        records = list(ledger.iter_events())
        head = ledger.head()
        self._head = (
            head.sequence, head.event_hash
        ) if head else (0, GENESIS_DIGEST)
        if records and (
            records[-1].sequence != self._head[0]
            or records[-1].event_hash != self._head[1]
        ):
            raise StaleLedgerProjection("Ledger changed during verified snapshot")
        self.descriptor = SourceDescriptor(
            subject_id="kiki", namespace=NAMESPACE,
            source_version=VERSION, source_hash=self._head[1],
            encoder_id=ENCODER, index_scope="canonical_metadata_only",
        )
        self._items = {}
        for record in records:
            safe = self._receipt(record)
            if safe is not None:
                self._items[record.event_id] = (
                    record.sequence,
                    MemoryCandidate(
                        subject_id="kiki", namespace=NAMESPACE,
                        record_id=record.event_id,
                        source_hash=self.descriptor.source_hash,
                        origin_class=safe[1], source_excerpt=safe[0],
                    ),
                )
        self._assert_fresh()

    @staticmethod
    def _receipt(record):
        if record.content_restrictions:
            # This intentionally drops every restricted record. A future
            # feature must not relax this without a separate authority gate.
            return None
        choice = _ALIASES.get(record.event_type)
        if choice is None:
            return None
        if record.event_type == EventType.EVIDENCE_INGESTED:
            if (record.epistemic_class != EpistemicClass.SOURCE_EVIDENCE
                    or record.claim_domain != ClaimDomain.EXTERNAL_FACT):
                return None
        elif (record.actor_kind != ActorKind.KIKI
              or record.actor_id != "kiki"):
            return None
        text, origin = choice
        # Append only controlled categories. Never surface text, content,
        # model self-reports, relationship claims or source/title fields.
        if record.event_type == EventType.DEVELOPMENTAL_OBSERVATION_RECORDED:
            kind = record.payload.get("observation_kind")
            if type(kind) is str and kind in _OBSERVATIONS:
                text += " kind " + kind.replace("_", " ")
        elif record.event_type == EventType.ENCOUNTER_RECORDED:
            kind = record.payload.get("encounter_type")
            if type(kind) is str and kind in _ENCOUNTERS:
                text += " kind " + kind
        return text, origin

    def _assert_fresh(self):
        self._ledger.verify_integrity()
        head = self._ledger.head()
        now = (head.sequence, head.event_hash) if head else (0, GENESIS_DIGEST)
        if now != self._head:
            raise StaleLedgerProjection(
                "Canonical history advanced; rebuild the disposable projection"
            )

    def search(self, query: str, *, top_k: int):
        self._assert_fresh()
        q = set(TOKENS.findall(query.lower()))
        scores = []
        for event_id, (sequence, item) in self._items.items():
            found = q & set(TOKENS.findall(item.source_excerpt))
            if found:
                scores.append((len(found) / len(q), sequence, event_id, item))
        scores.sort(key=lambda x: (-x[0], x[1], x[2]))
        found = [
            MemoryCandidate(
                subject_id=i.subject_id, namespace=i.namespace,
                record_id=i.record_id, source_hash=i.source_hash,
                origin_class=i.origin_class, source_excerpt=i.source_excerpt,
                score=float(score),
            )
            for score, _, _, i in scores[:top_k]
        ]
        self._assert_fresh()
        return found

    def get(self, record_id: str):
        self._assert_fresh()
        found = self._items.get(record_id)
        self._assert_fresh()
        return found[1] if found else None
