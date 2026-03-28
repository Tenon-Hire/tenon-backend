"""Application module for evaluations services evaluations evaluator evidence text service workflows."""

from __future__ import annotations

from typing import Any

from app.evaluations.services.evaluations_services_evaluations_evaluator_helpers_service import (
    _to_excerpt,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    DayEvaluationInput,
)


def _build_text_day_evidence(day: DayEvaluationInput) -> list[dict[str, Any]]:
    excerpt = _to_excerpt(day.content_text)
    if excerpt is None and day.content_json is not None:
        excerpt = _to_excerpt(str(day.content_json))
    if excerpt is None:
        return []
    return [
        {
            "kind": "reflection",
            "ref": str(day.submission_id or f"day-{day.day_index}"),
            "excerpt": excerpt,
        }
    ]


def _fallback_evidence(day: DayEvaluationInput) -> list[dict[str, Any]]:
    return [
        {
            "kind": "reflection",
            "ref": str(day.submission_id or f"day-{day.day_index}"),
            "excerpt": "No substantive evidence was available for this day at evaluation time.",
        }
    ]


__all__ = ["_build_text_day_evidence", "_fallback_evidence"]
