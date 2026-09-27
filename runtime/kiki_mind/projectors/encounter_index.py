from __future__ import annotations

from typing import Any, Mapping

from ..models import EventRecord, EventType


class EncounterIndexProjectorV1:
    """Deterministic encounter index over canonical encounter events."""

    name = "encounter-index"
    version = "1"

    def initial_state(self) -> Mapping[str, Any]:
        return {"entries": {}}

    def apply(
        self,
        state: Mapping[str, Any],
        event: EventRecord,
    ) -> Mapping[str, Any]:
        result = {"entries": dict(state["entries"])}
        if event.event_type != EventType.ENCOUNTER_RECORDED:
            return result

        representation_id = str(event.payload["representation_id"])
        mode = str(event.payload["mode"])
        activation_version = str(
            event.payload["activation_function_version"]
        )
        encounter_type = str(event.payload["encounter_type"])
        key = "\u001f".join(
            (representation_id, mode, activation_version)
        )

        prior = result["entries"].get(key)
        if prior is None:
            entry = {
                "representation_id": representation_id,
                "mode": mode,
                "activation_function_version": activation_version,
                "encounter_count": 1,
                "first_sequence": event.sequence,
                "last_sequence": event.sequence,
                "last_encounter_type": encounter_type,
                "source_event_ids": [event.event_id],
            }
        else:
            entry = {
                "representation_id": prior["representation_id"],
                "mode": prior["mode"],
                "activation_function_version":
                    prior["activation_function_version"],
                "encounter_count": int(prior["encounter_count"]) + 1,
                "first_sequence": int(prior["first_sequence"]),
                "last_sequence": event.sequence,
                "last_encounter_type": encounter_type,
                "source_event_ids": list(prior["source_event_ids"])
                    + [event.event_id],
            }

        result["entries"][key] = entry
        return result
