"""Application module for evaluations services evaluations evaluator evidence transcript service workflows."""

from __future__ import annotations

from typing import Any

from app.evaluations.services.evaluations_services_evaluations_evaluator_helpers_service import (
    _segment_end_ms,
    _segment_start_ms,
    _segment_text,
    _to_excerpt,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    DayEvaluationInput,
)


def _build_transcript_day_evidence(day: DayEvaluationInput) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for segment in day.transcript_segments[:3]:
        if not isinstance(segment, dict):
            continue
        start_ms = _segment_start_ms(segment)
        end_ms = _segment_end_ms(segment)
        if start_ms is None or end_ms is None:
            continue
        if end_ms < start_ms:
            end_ms = start_ms
        transcript_item: dict[str, Any] = {
            "kind": "transcript",
            "ref": str(day.transcript_reference or day.submission_id or "transcript"),
            "startMs": start_ms,
            "endMs": end_ms,
        }
        excerpt = _to_excerpt(_segment_text(segment), max_chars=220)
        if excerpt is not None:
            transcript_item["excerpt"] = excerpt
        evidence.append(transcript_item)
    return evidence


__all__ = ["_build_transcript_day_evidence"]
