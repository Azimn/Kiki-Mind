"""bAbI v0.4 external text as verified, synthetic-only Kiki source evidence.

Data from a public, fixed Git commit; never from private Kiki history.
A separate disposable EventLedger is built per question prefix, so a memory
query physically cannot access subsequent facts or another story episode.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
from pathlib import Path
import random
import re

from pretorius_connectome.cognition_port import MemoryCandidate, SourceDescriptor, MemorySourceMismatch
from runtime.kiki_mind.ledger import EventLedger
from runtime.kiki_mind.models import EventType, ActorKind, EpistemicClass, ClaimDomain

REVISION = "642a9ade9c92677b970b1bc9921cafb0764d2ed7"
ORIGINAL = {
    "qa1": ("qa1_single-supporting-fact_test.txt", "8f9586848f7b0afdccb25328feeb04d561c31756"),
    "qa2": ("qa2_two-supporting-facts_test.txt", "6deccd0cf07947ff525839a7b4643c6e0afe1b92"),
    "qa6": ("qa6_yes-no-questions_test.txt", "da25e9fd5bb7d69c7150b208051b1413fd91ff2b"),
}
NAMESPACE = "kiki.external_babi.v04"
TOKEN = re.compile(r"[a-z]+")
STOP = frozenset({"the","is","in","where","who","a","to","did","was","there","back","of","what","yes","no"})
LINE = re.compile(r"^([0-9]+) (.+)$")


def blob_sha(payload: bytes) -> str:
    return sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


@dataclass(frozen=True)
class BenchmarkQuestion:
    task: str
    ordinal: int
    episode: int
    line: int
    question: str
    gold_answer: str
    support: tuple[int, ...]
    facts: tuple[tuple[int,str], ...]


def load_babi(path: Path, *, task: str, limit: int = 40) -> tuple[BenchmarkQuestion, ...]:
    filename, git_sha = ORIGINAL[task]
    if path.name != filename:
        raise MemorySourceMismatch("Wrong benchmark source filename")
    data = path.read_bytes()
    if blob_sha(data) != git_sha:
        raise MemorySourceMismatch("External bAbI test dataset hash does not match Git pin")
    results = []
    episode = 0
    facts: list[tuple[int,str]] = []
    for raw_line in data.decode("utf-8").splitlines():
        if not raw_line.strip():
            continue
        m = LINE.fullmatch(raw_line)
        if not m:
            raise MemorySourceMismatch("Invalid upstream benchmark line")
        number = int(m.group(1))
        content = m.group(2)
        if number == 1:
            episode += 1
            facts = []
        if "\t" in content:
            parts = content.split("\t")
            if len(parts) != 3:
                raise MemorySourceMismatch("Unexpected QA fields")
            q, answer, support = parts
            if not answer.strip():
                raise MemorySourceMismatch("Empty benchmark gold")
            results.append(BenchmarkQuestion(
                task, len(results)+1, episode, number, q.strip(),
                answer.strip(), tuple(int(x) for x in support.split()),
                tuple(facts),
            ))
            if len(results) == limit:
                return tuple(results)
        else:
            facts.append((number, content.strip()))
    if len(results) != limit:
        raise MemorySourceMismatch("Benchmark has fewer questions than registered")
    return tuple(results)


def record_id(question: BenchmarkQuestion, line: int) -> str:
    return f"{question.task}-{question.ordinal:04d}-{line:04d}"


def canonical(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class BabiKikiSource:
    """In-process, read-only evidence index bound to one verified story prefix."""

    def __init__(self, ledger: EventLedger, question: BenchmarkQuestion, *, source_blob: str):
        if not isinstance(ledger, EventLedger):
            raise TypeError("Verified EventLedger is required")
        ledger.verify_integrity()
        self._ledger = ledger
        self.question = question
        self._records = []
        seen = set()
        for event in ledger.iter_events():
            if (event.event_type != EventType.EVIDENCE_INGESTED
                    or event.actor_kind != ActorKind.SYSTEM
                    or event.epistemic_class != EpistemicClass.SOURCE_EVIDENCE
                    or event.claim_domain != ClaimDomain.EXTERNAL_FACT
                    or event.content_restrictions
                    or event.payload.get("source_owner") != "kiki"
                    or event.payload.get("source_blob") != source_blob):
                raise MemorySourceMismatch("Non-authorized source event in bAbI ledger")
            self._records.append(event)
            if event.event_id in seen:
                raise MemorySourceMismatch("Duplicate source event")
            seen.add(event.event_id)
        if len(self._records) != len(question.facts):
            raise MemorySourceMismatch("Evidence ledger is not exactly the question prefix")
        for ev, (line, text) in zip(self._records, question.facts):
            if (ev.event_id != record_id(question,line)
                    or ev.payload.get("text") != text
                    or ev.payload.get("line") != line
                    or not line < question.line):
                raise MemorySourceMismatch("Source was reordered, truncated or future-contaminated")
        h = ledger.head()
        if h is None:
            raise MemorySourceMismatch("Empty evidence ledger")
        self._head = (h.sequence,h.event_hash)
        self.descriptor = SourceDescriptor(
            subject_id="kiki", namespace=NAMESPACE,
            source_version=f"{question.task}.{question.ordinal:04d}.prefix",
            source_hash=sha256(canonical({
                "git_blob": source_blob, "event_hash": h.event_hash,
                "task": question.task, "episode": question.episode,
                "before_line": question.line
            }).encode("utf-8")).hexdigest(),
            encoder_id="babi-lexical-v04", index_scope="single_story_prefix",
        )
        self._items = tuple(MemoryCandidate(
            subject_id="kiki", namespace=NAMESPACE, record_id=e.event_id,
            source_hash=self.descriptor.source_hash,
            origin_class="external_document", source_excerpt=e.payload["text"]
        ) for e in self._records)

    def _fresh(self):
        self._ledger.verify_integrity()
        h=self._ledger.head()
        if h is None or (h.sequence,h.event_hash)!=self._head:
            raise MemorySourceMismatch("Synthetic episode evidence ledger changed")

    def records(self) -> tuple[MemoryCandidate, ...]:
        self._fresh()
        return self._items

    def search(self, query: str, *, top_k: int) -> list[MemoryCandidate]:
        self._fresh()
        q = set(TOKEN.findall(query.lower())) - STOP
        # Intent is learned from the literal question words ONLY, not the
        # benchmark answer, oracle supports, or synthetic sidecar.
        ranked = []
        for index, item in enumerate(self._items):
            s = set(TOKEN.findall(item.source_excerpt.lower())) - STOP
            overlap = len(q & s)
            if overlap:
                ranked.append((overlap, index, item))
        ranked.sort(key=lambda t: (-t[0], -t[1]))
        output = [
            MemoryCandidate(subject_id=i.subject_id,namespace=i.namespace,
                            record_id=i.record_id,source_hash=i.source_hash,
                            origin_class=i.origin_class,source_excerpt=i.source_excerpt,
                            score=float(overlap/ max(1,len(q))))
            for overlap, _, i in ranked[:top_k]
        ]
        self._fresh()
        return output

    def random_candidates(self, query: str, *, top_k:int):
        self._fresh()
        items=list(self._items)
        random.Random(int(sha256(query.encode()).hexdigest(),16)).shuffle(items)
        self._fresh()
        return tuple(items[:top_k])

    def get(self, record_id: str):
        self._fresh()
        found=next((x for x in self._items if x.record_id==record_id),None)
        self._fresh()
        return found
