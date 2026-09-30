"""Implementation 004: disposable retrieval and bounded Subjective Frames.

Retrieval is an accessibility organ, not an authority organ.  The structured
epistemic envelope is carried from canonical EventRecord to frame receipt and
is never inferred from similarity, frequency, renderer output, or text.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Protocol, Sequence

from .ledger import EventLedger
from .models import EventRecord

GENESIS_HASH = "GENESIS"
RETRIEVAL_PROJECTION_VERSION = "004.0"
FRAME_SCHEMA_VERSION = "004.0"


class RetrievalError(RuntimeError):
    pass


class RetrievalBindingMismatch(RetrievalError):
    pass


class RetrievalCorruption(RetrievalError):
    pass


class ConstitutionalContextMissing(RetrievalError):
    pass


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RetrievalRegime:
    projector_id: str
    projector_version: str
    retrieval_version: str
    embedding_id: str
    embedding_version: str
    chunking_version: str
    policy_version: str
    similarity_metric: str = "token_overlap"

    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class EpistemicEnvelope:
    source_event_id: str
    source_sequence: int
    event_type: str
    epistemic_class: str
    claim_domain: str
    content_restrictions: tuple[str, ...]
    renderer_mediated: bool
    renderer_id: str | None


@dataclass(frozen=True)
class RetrievalItem:
    record_id: str
    text: str
    envelope: EpistemicEnvelope


@dataclass(frozen=True)
class RetrievalHit:
    item: RetrievalItem
    score: float


@dataclass(frozen=True)
class ConstitutionalComponent:
    component_id: str
    version: str
    text: str


@dataclass(frozen=True)
class FrameItem:
    source: str
    record_id: str
    text: str
    envelope: EpistemicEnvelope | None
    score: float | None = None


@dataclass(frozen=True)
class FrameReceipt:
    frame_id: str
    schema_version: str
    canonical_sequence: int
    canonical_tail_hash: str
    retrieval_regime_digest: str
    selector_version: str
    renderer_adapter_version: str
    renderer_id: str
    session_id: str
    constitutional_components: tuple[tuple[str, str], ...]
    selected_record_ids: tuple[str, ...]
    omitted_record_ids: tuple[str, ...]
    budget_chars: int
    structured_frame_digest: str


@dataclass(frozen=True)
class SubjectiveFrame:
    items: tuple[FrameItem, ...]
    receipt: FrameReceipt


class RetrievalPolicy(Protocol):
    version: str

    def rank(
        self,
        query: str,
        items: Sequence[RetrievalItem],
    ) -> Sequence[RetrievalHit]: ...


class TokenOverlapPolicy:
    """Offline deterministic baseline; replaceable without changing authority."""

    version = "token-overlap-v1"

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {x.strip(".,!?;:()[]{}\"'").lower() for x in text.split() if x.strip()}

    def rank(self, query: str, items: Sequence[RetrievalItem]) -> Sequence[RetrievalHit]:
        q = self._tokens(query)
        hits = []
        for item in items:
            t = self._tokens(item.text)
            score = (len(q & t) / len(q | t)) if (q or t) else 0.0
            hits.append(RetrievalHit(item, score))
        return tuple(sorted(hits, key=lambda h: (-h.score, h.item.record_id)))


def _event_text(event: EventRecord) -> str:
    # Projection text is deliberately boring and reconstructible.  Payload
    # structure remains canonical in the ledger; this string has no authority.
    return _json(dict(event.payload))


def _item_from_event(event: EventRecord) -> RetrievalItem:
    envelope = EpistemicEnvelope(
        source_event_id=event.event_id,
        source_sequence=event.sequence,
        event_type=event.event_type.value,
        epistemic_class=event.epistemic_class.value,
        claim_domain=event.claim_domain.value,
        content_restrictions=tuple(sorted(x.value for x in event.content_restrictions)),
        renderer_mediated=event.renderer_mediated,
        renderer_id=event.renderer_id,
    )
    return RetrievalItem(
        record_id=f"event:{event.event_id}",
        text=_event_text(event),
        envelope=envelope,
    )


class RetrievalProjection:
    """Disposable JSON projection bound to an exact canonical/regime head."""

    def __init__(self, ledger: EventLedger, path: str | Path, regime: RetrievalRegime):
        self.ledger = ledger
        self.path = Path(path)
        self.regime = regime

    def _head(self) -> tuple[int, str]:
        head = self.ledger.head()
        return (head.sequence, head.event_hash) if head else (0, GENESIS_HASH)

    def _material(self, through_sequence: int | None = None) -> dict:
        head_sequence, head_hash = self._head()
        target = head_sequence if through_sequence is None else through_sequence
        if target < 0 or target > head_sequence:
            raise RetrievalBindingMismatch("retrieval target outside canonical ledger")
        if target == 0:
            tail_hash = GENESIS_HASH
        else:
            event = self.ledger.get_event_by_sequence(target)
            if event is None:
                raise RetrievalBindingMismatch("retrieval target is not canonical")
            tail_hash = event.event_hash
        items = [_item_from_event(e) for e in self.ledger.iter_events(through_sequence=target)]
        item_dicts = [asdict(i) for i in items]
        body = {
            "projection_version": RETRIEVAL_PROJECTION_VERSION,
            "regime": asdict(self.regime),
            "regime_digest": self.regime.digest(),
            "canonical_sequence": target,
            "canonical_tail_hash": tail_hash,
            "items": item_dicts,
        }
        body["index_digest"] = _digest(body)
        return body

    def rebuild(self) -> dict:
        self.ledger.verify_integrity()
        body = self._material()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(_json(body), encoding="utf-8")
        return body

    def incremental(self) -> dict:
        # Correctness first: 004 defines incremental equivalence by rebuilding
        # the disposable projection and requiring identical semantic material.
        expected = self._material()
        if self.path.exists():
            current = self.load(require_current=False)
            if current["canonical_sequence"] > expected["canonical_sequence"]:
                raise RetrievalBindingMismatch("retrieval projection is ahead of canon")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(_json(expected), encoding="utf-8")
        return expected

    def load(self, *, require_current: bool = True) -> dict:
        try:
            body = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RetrievalCorruption("retrieval projection is unreadable") from exc
        digest = body.get("index_digest")
        check = dict(body)
        check.pop("index_digest", None)
        if digest != _digest(check):
            raise RetrievalCorruption("retrieval projection digest mismatch")
        if body.get("projection_version") != RETRIEVAL_PROJECTION_VERSION:
            raise RetrievalBindingMismatch("retrieval projection version mismatch")
        if body.get("regime_digest") != self.regime.digest() or body.get("regime") != asdict(self.regime):
            raise RetrievalBindingMismatch("retrieval regime mismatch; rebuild required")
        if require_current:
            sequence, tail_hash = self._head()
            if body.get("canonical_sequence") != sequence or body.get("canonical_tail_hash") != tail_hash:
                raise RetrievalBindingMismatch("retrieval projection is stale")
        return body

    def items(self) -> tuple[RetrievalItem, ...]:
        body = self.load()
        out = []
        for raw in body["items"]:
            env = EpistemicEnvelope(**raw["envelope"])
            out.append(RetrievalItem(raw["record_id"], raw["text"], env))
        return tuple(out)


class SubjectiveFrameBuilder:
    def __init__(
        self,
        ledger: EventLedger,
        projection: RetrievalProjection,
        *,
        required_constitution: Mapping[str, str],
        selector_version: str = "selector-004.0",
    ):
        self.ledger = ledger
        self.projection = projection
        self.required_constitution = dict(required_constitution)
        self.selector_version = selector_version

    def build(
        self,
        *,
        query: str,
        constitution: Sequence[ConstitutionalComponent],
        policy: RetrievalPolicy,
        renderer_id: str,
        renderer_adapter_version: str,
        session_id: str,
        budget_chars: int = 6000,
        max_retrieved: int = 8,
    ) -> SubjectiveFrame:
        provided = {c.component_id: c for c in constitution}
        for cid, version in self.required_constitution.items():
            if cid not in provided or provided[cid].version != version:
                raise ConstitutionalContextMissing(f"required constitutional component missing/mismatched: {cid}")

        sequence, tail_hash = self.projection._head()
        hits = policy.rank(query, self.projection.items())

        items: list[FrameItem] = []
        used = 0
        for component in sorted(constitution, key=lambda c: c.component_id):
            fi = FrameItem("constitution", f"constitution:{component.component_id}", component.text, None)
            used += len(component.text)
            if used > budget_chars:
                raise ConstitutionalContextMissing("budget cannot fit required constitutional context")
            items.append(fi)

        selected, omitted = [], []
        for hit in hits:
            if len(selected) >= max_retrieved or used + len(hit.item.text) > budget_chars:
                omitted.append(hit.item.record_id)
                continue
            items.append(FrameItem("retrieval", hit.item.record_id, hit.item.text, hit.item.envelope, hit.score))
            selected.append(hit.item.record_id)
            used += len(hit.item.text)

        structured = [asdict(x) for x in items]
        frame_digest = _digest(structured)
        receipt_material = {
            "schema_version": FRAME_SCHEMA_VERSION,
            "canonical_sequence": sequence,
            "canonical_tail_hash": tail_hash,
            "retrieval_regime_digest": self.projection.regime.digest(),
            "selector_version": self.selector_version,
            "renderer_adapter_version": renderer_adapter_version,
            "renderer_id": renderer_id,
            "session_id": session_id,
            "constitutional_components": tuple(sorted((c.component_id, c.version) for c in constitution)),
            "selected_record_ids": tuple(selected),
            "omitted_record_ids": tuple(omitted),
            "budget_chars": budget_chars,
            "structured_frame_digest": frame_digest,
        }
        frame_id = _digest(receipt_material)
        return SubjectiveFrame(tuple(items), FrameReceipt(frame_id=frame_id, **receipt_material))


def renderer_proposal(ledger: EventLedger, proposal):
    """Renderer writes have exactly one canonical route: the Transition Gate."""
    return ledger.commit(proposal)
