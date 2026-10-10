"""Question interpretation and world-state tracking WITHOUT answer/intent oracle.

Strictly fixed-rule parser for externally authored bAbI tasks 1, 2 and 6.
Never consumes gold answers, supporting IDs, or data outside returned evidence.
Unsupported language and incomplete state yield an explicit abstention.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

MOVE = re.compile(
    r"^([A-Z][a-z]+) (?:went(?: back)?|moved|journeyed|travelled) to the ([a-z]+)\.$"
)
TAKE = re.compile(
    r"^([A-Z][a-z]+) (?:got|grabbed|took|picked up) the ([a-z]+)(?: there)?\.$"
)
DROP = re.compile(
    r"^([A-Z][a-z]+) (?:put down|discarded|left|dropped) the ([a-z]+)(?: there)?\.$"
)
WHERE = re.compile(r"^Where is (?:the )?([A-Za-z]+)\?$")
YESNO = re.compile(r"^Is ([A-Za-z]+) in the ([a-z]+)\?$")


@dataclass(frozen=True)
class Answer:
    value: str | None
    cited: tuple[str,...]
    parser_supported: bool


def interpret(question: str):
    m = WHERE.fullmatch(question)
    if m:
        return ("where", m.group(1).lower(), None)
    m = YESNO.fullmatch(question)
    if m:
        return ("yesno", m.group(1).lower(), m.group(2).lower())
    return None


def reason(question: str, candidates) -> Answer:
    intent=interpret(question)
    if intent is None:
        return Answer(None, (), False)

    people = {}   # person -> (location, source ID)
    holder = {}   # object -> (person, possession source ID)
    ground = {}   # object -> (location, source IDs)
    parsed = []
    for entry in candidates:
        text = getattr(entry,"text",None)
        if text is None:
            text=entry.source_excerpt
        try:
            n=int(entry.record_id.rsplit("-",1)[-1])
        except (ValueError, AttributeError):
            return Answer(None, (), False)
        parsed.append((n,entry.record_id,text))
    parsed.sort()
    for _, rid, sentence in parsed:
        if m := MOVE.fullmatch(sentence):
            who = m.group(1).lower()
            loc = m.group(2).lower()
            people[who] = (loc, rid)
        elif m := TAKE.fullmatch(sentence):
            who = m.group(1).lower()
            obj = m.group(2).lower()
            holder[obj] = (who, rid)
            ground.pop(obj, None)
        elif m := DROP.fullmatch(sentence):
            who = m.group(1).lower()
            obj = m.group(2).lower()
            if holder.get(obj, (None,None))[0] == who:
                del holder[obj]
            state = people.get(who)
            if state:
                ground[obj] = (state[0], tuple(dict.fromkeys((rid,state[1]))))
            else:
                ground.pop(obj, None)  # cannot infer a location
        else:
            # Other syntax remains uninterpreted: no invented world facts.
            continue

    mode, ent, check = intent
    location = people.get(ent)
    citations = ()
    if location is not None:
        value = location[0]
        citations = (location[1],)
    elif ent in holder:
        owner, pickup_id = holder[ent]
        if owner in people:
            value, movement_id = people[owner]
            citations = tuple(dict.fromkeys((pickup_id, movement_id)))
        else:
            value = None
    elif ent in ground:
        value, citations = ground[ent]
    else:
        value = None

    if value is None:
        return Answer(None, (), True)
    if mode == "yesno":
        # "no" means contradictory *observed current location*,
        # not closed-world absence of any observation.
        return Answer("yes" if value == check else "no", citations, True)
    return Answer(value, citations, True)
