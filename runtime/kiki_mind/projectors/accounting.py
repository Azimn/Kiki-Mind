"""Aggressively boring accounting projector.

Before Kiki gets anything resembling psychology, this module proves that the
projection machinery can count receipts without becoming the diary.
"""

from __future__ import annotations

from typing import Any, Mapping

from ..models import ClaimDomain, EventRecord, EventType


class LedgerAccountingProjectorV1:
    """Reference accounting projector for Implementation 002.

    It counts. It indexes. It does not have opinions. Honestly, iconic.
    """

    name = "ledger-accounting"
    version = "1"

    def initial_state(self) -> Mapping[str, Any]:
        return {
            "event_count": 0,
            "renderer_mediated_count": 0,
            "encounter_count": 0,
            "event_type_counts": {},
            "latest_governance_event_ids": {},
        }

    def apply(
        self,
        state: Mapping[str, Any],
        event: EventRecord,
    ) -> Mapping[str, Any]:
        result = {
            "event_count": int(state["event_count"]) + 1,
            "renderer_mediated_count": int(
                state["renderer_mediated_count"]
            ),
            "encounter_count": int(state["encounter_count"]),
            "event_type_counts": dict(state["event_type_counts"]),
            "latest_governance_event_ids": dict(
                state["latest_governance_event_ids"]
            ),
        }

        if event.renderer_mediated:
            result["renderer_mediated_count"] += 1

        if event.event_type == EventType.ENCOUNTER_RECORDED:
            result["encounter_count"] += 1

        key = event.event_type.value
        result["event_type_counts"][key] = (
            int(result["event_type_counts"].get(key, 0)) + 1
        )

        if event.claim_domain == ClaimDomain.GOVERNANCE:
            result["latest_governance_event_ids"][key] = event.event_id

        return result
