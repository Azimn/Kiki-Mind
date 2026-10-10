"""Synthetic public-content source for v0.3; NOT Kiki's live memory adapter.

Requires source evidence already committed via the real Kiki EventLedger, checks
source hashes and owner/visibility before indexing. All data are versioned
synthetic development fixtures. Does not mutate the event ledger.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

from pretorius_connectome.cognition_port import (
    MemoryCandidate, MemorySourceMismatch, SourceDescriptor,
)
from runtime.kiki_mind.ledger import EventLedger
from runtime.kiki_mind.models import (
    ActorKind, ClaimDomain, EpistemicClass, EventType,
)

SUBJECT = "kiki"
NAMESPACE = "kiki.synthetic.authorized_content.v03"
ENCODER = "lexical-typed-synthetic-v03"
SCHEMA = "kiki-semantic-evidence-pilot/0.3"
SPLIT = "all_synthetic_development_only"
WORDS = re.compile(r"[a-z0-9]+")
STOP = frozenset((
    "the", "a", "an", "is", "was", "were", "are", "at", "in", "to",
    "what", "where", "who", "which", "of", "and", "for", "does",
    "did", "have", "has", "on", "before", "after", "would",
    "be", "its", "it", "recorded", "place", "last", "when",
    "keeper", "keeps", "owner", "owns", "hold", "holds", "belong",
    "belongs", "room", "station", "with", "rumors", "spread",
    "otherwise", "says", "does", "from", "by"
))
ALLOWED_STATUS = {"authored_fact", "reported_rumor"}
RELATIONS = {"owned_by", "located_at"}


class SyntheticSourceViolation(MemorySourceMismatch):
    pass


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(data):
    return sha256(canonical(data).encode("utf-8")).hexdigest()


def query_tokens(text: str):
    return set(WORDS.findall(text.lower())) - STOP


class AuthorizedSyntheticContentSource:
    """Fixed-source, read-only, subject-specific typed evidence.

    Scope limited to fixtures: underlying EventLedger must contain source
    documentation, and each permitted item must exactly match that record's
    SHA, source text, actor class, owner, and restriction state. This class
    never makes private Kiki canonical content visible.
    """

    def __init__(self, ledger: EventLedger, fixture: dict):
        if not isinstance(ledger, EventLedger):
            raise TypeError("Verified Kiki EventLedger is mandatory")
        if not isinstance(fixture, dict) or fixture.get("schema") != SCHEMA:
            raise SyntheticSourceViolation("Unknown synthetic fixture schema")
        if fixture.get("classification") != "synthetic-public-fixture-only":
            raise SyntheticSourceViolation("Real-world/production inputs forbidden")
        self._ledger = ledger
        self._fixture = fixture
        self._fixture_hash = digest(fixture)
        ledger.verify_integrity()
        head = ledger.head()
        if head is None:
            raise SyntheticSourceViolation("Synthetic source requires committed records")
        self._head = (head.sequence, head.event_hash)
        combined = digest({"fixture": self._fixture_hash, "ledger_head": head.event_hash})
        self.descriptor = SourceDescriptor(
            subject_id=SUBJECT, namespace=NAMESPACE,
            source_version="synthetic-content-v03",
            source_hash=combined, encoder_id=ENCODER, index_scope=SPLIT,
        )
        self._items: dict[str, MemoryCandidate] = {}
        self._load_permitted()
        self._assert_fresh()

    def _assert_fresh(self):
        self._ledger.verify_integrity()
        head = self._ledger.head()
        if head is None or (head.sequence, head.event_hash) != self._head:
            raise SyntheticSourceViolation("Source advanced; rebuild synthetic content projection")

    def _load_permitted(self):
        seen = set()
        for doc in self._fixture["documents"]:
            if doc["id"] in seen:
                raise SyntheticSourceViolation("Duplicate synthetic source ID")
            seen.add(doc["id"])
            ev = self._ledger.get_event(doc["ledger_event_id"])
            if ev is None or ev.event_type != EventType.EVIDENCE_INGESTED:
                raise SyntheticSourceViolation("Missing documented source receipt")
            if (ev.actor_kind != ActorKind.SYSTEM
                    or ev.epistemic_class != EpistemicClass.SOURCE_EVIDENCE
                    or ev.claim_domain != ClaimDomain.EXTERNAL_FACT
                    or ev.payload.get("document_sha256") != digest(doc)
                    or ev.payload.get("title") != doc["source_text"]
                    or ev.payload.get("source_owner") != doc["subject_id"]):
                raise SyntheticSourceViolation("Source document does not match canonical event")
            status = doc["claim"]["status"]
            if status not in ALLOWED_STATUS or doc["claim"]["relation"] not in RELATIONS:
                raise SyntheticSourceViolation("Unsupported synthetic source claim")
            if doc["subject_id"] != SUBJECT or doc["visibility"] != "kiki":
                continue
            if ev.content_restrictions:
                continue
            if status == "authored_fact":
                origin = "authored_fiction"
            else:
                origin = "external_document"
            envelope = {
                "source_id": doc["id"],
                "event_id": ev.event_id,
                "claim": doc["claim"],
                "claim_kind": status,
                "authority": "fictional_world_only",
            }
            evidence = MemoryCandidate(
                subject_id=SUBJECT, namespace=NAMESPACE,
                record_id=doc["id"], source_hash=self.descriptor.source_hash,
                origin_class=origin, source_excerpt=canonical(envelope),
            )
            self._items[doc["id"]] = evidence

    def search(self, query: str, *, top_k: int):
        self._assert_fresh()
        q = query_tokens(query)
        if not q:
            return []
        scores = []
        for rid, item in self._items.items():
            # Human-readable indexed text comes from typed source values.
            body = json.loads(item.source_excerpt)
            claim = body["claim"]
            corpus = " ".join([
                claim["entity"], claim["relation"].replace("_", " "),
                claim["value"], item.source_excerpt,
            ])
            matched = len(q & query_tokens(corpus))
            if matched:
                scores.append((matched, rid, item))
        scores.sort(key=lambda x: (-x[0], x[1]))
        results = [
            MemoryCandidate(
                subject_id=SUBJECT, namespace=NAMESPACE,
                record_id=item.record_id, source_hash=item.source_hash,
                origin_class=item.origin_class, source_excerpt=item.source_excerpt,
                score=float(score / len(q)),
            )
            for score, _, item in scores[:top_k]
        ]
        self._assert_fresh()
        return results

    def get(self, record_id: str):
        self._assert_fresh()
        item = self._items.get(record_id)
        self._assert_fresh()
        return item

    def uniform_candidates(self, *, query: str, top_k: int):
        """Fixed-seed non-ranked source selection; same visible source population.

        The caller may use this as a calibration control, but its *relevance*
        is not matched to ranked retrieval.
        """
        import random
        self._assert_fresh()
        items = list(self._items.values())
        random.Random(int(sha256(query.encode("utf-8")).hexdigest(), 16)).shuffle(items)
        return items[:top_k]
