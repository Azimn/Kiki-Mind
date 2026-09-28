"""Developmental evidence index, not a personality horoscope.

This projector answers one boring question: which canonical observations exist,
under which renderer and context, and how do commitment lineages connect?

It does not decide whether Kiki became happier, braver, wiser, more autonomous,
or more mature. That fabulous drama belongs to later derived interpretation.
"""

from __future__ import annotations

from typing import Any, Mapping

from ..models import (
    DevelopmentalObservationKind,
    EventRecord,
    EventType,
)


class DevelopmentalEvidenceIndexV1:
    """Trace developmental receipts without inventing developmental meaning."""

    name = "developmental-evidence-index"
    version = "1"

    def initial_state(self) -> Mapping[str, Any]:
        return {
            "observation_count": 0,
            "by_kind": {},
            "by_renderer": {},
            "entries": [],
            "commitments": {},
        }

    def apply(
        self,
        state: Mapping[str, Any],
        event: EventRecord,
    ) -> Mapping[str, Any]:
        result = {
            "observation_count": int(state["observation_count"]),
            "by_kind": {
                key: list(value)
                for key, value in state["by_kind"].items()
            },
            "by_renderer": {
                key: list(value)
                for key, value in state["by_renderer"].items()
            },
            "entries": list(state["entries"]),
            "commitments": {
                key: {
                    "event_ids": list(value["event_ids"]),
                    "latest_recorded_phase": value[
                        "latest_recorded_phase"
                    ],
                }
                for key, value in state["commitments"].items()
            },
        }

        if (
            event.event_type
            != EventType.DEVELOPMENTAL_OBSERVATION_RECORDED
        ):
            return result

        kind = DevelopmentalObservationKind(
            str(event.payload["observation_kind"])
        )
        renderer_id = event.renderer_id or "unknown"
        context = event.payload["context"]

        entry = {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "observation_kind": kind.value,
            "renderer_id": renderer_id,
            "model_id": context["model_id"],
            "provider_id": context["provider_id"],
            "runtime_id": context["runtime_id"],
            "modality": context["modality"],
            "context_provenance": context["context_provenance"],
        }

        result["observation_count"] += 1
        result["entries"].append(entry)
        result["by_kind"].setdefault(kind.value, []).append(
            event.event_id
        )
        result["by_renderer"].setdefault(renderer_id, []).append(
            event.event_id
        )

        if kind == DevelopmentalObservationKind.COMMITMENT:
            commitment_id = str(event.payload["commitment_id"])
            prior = result["commitments"].get(commitment_id)
            event_ids = (
                list(prior["event_ids"])
                if prior is not None
                else []
            )
            event_ids.append(event.event_id)
            result["commitments"][commitment_id] = {
                "event_ids": event_ids,
                "latest_recorded_phase": str(event.payload["phase"]),
            }

        return result
