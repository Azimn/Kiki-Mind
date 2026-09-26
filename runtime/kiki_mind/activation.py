from dataclasses import dataclass
from typing import Iterable
from .models import EventRecord, EventType

@dataclass(frozen=True)
class ActivationValue:
    representation_id: str
    mode: str
    value: float
    function_version: str

class CountActivationV1:
    """Reference projector only: proves encounter -> derived activation."""
    version = "count-activation-v1"
    def project(self, events: Iterable[EventRecord]) -> list[ActivationValue]:
        counts = {}
        for event in events:
            if event.event_type != EventType.ENCOUNTER_RECORDED:
                continue
            key = (str(event.payload["representation_id"]), str(event.payload["mode"]))
            counts[key] = counts.get(key, 0.0) + 1.0
        return [ActivationValue(r,m,v,self.version) for (r,m),v in sorted(counts.items())]
