"""Disposable activation with good provenance and zero mystical glitter.

Activation may feel psychologically interesting later, but here it stays
mechanical: committed encounters go in, reconstructible numbers come out.
If the ledger survives, this state can lose a shoe at midnight and come back.
"""

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
    """Reference projector proving encounter -> derived activation.

    Very Clueless closet computer: count what is actually there, do not invent
    an outfit because it would complete the look.
    """

    version = "count-activation-v1"

    def project(
        self,
        events: Iterable[EventRecord],
    ) -> list[ActivationValue]:
        counts: dict[tuple[str, str], float] = {}

        for event in events:
            if event.event_type != EventType.ENCOUNTER_RECORDED:
                continue
            if (
                event.payload.get("activation_function_version")
                != self.version
            ):
                continue

            key = (
                str(event.payload["representation_id"]),
                str(event.payload["mode"]),
            )
            counts[key] = counts.get(key, 0.0) + 1.0

        return [
            ActivationValue(
                representation_id=representation_id,
                mode=mode,
                value=value,
                function_version=self.version,
            )
            for (representation_id, mode), value
            in sorted(counts.items())
        ]
