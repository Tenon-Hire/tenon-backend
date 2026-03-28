"""Application module for evaluations services evaluations evaluator scoring service workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATION_HIRE,
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
    EVALUATION_RECOMMENDATION_NO_HIRE,
    EVALUATION_RECOMMENDATION_STRONG_HIRE,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_helpers_service import (
    _segment_text,
    _to_excerpt,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    DayEvaluationInput,
)


def _score_for_day(
    day: DayEvaluationInput, evidence: Sequence[dict[str, Any]]
) -> float:
    score = 0.08 + min(0.4, 0.12 * len(evidence))
    kinds = {str(item.get("kind", "")) for item in evidence}
    if day.day_index in {1, 5}:
        excerpt = _to_excerpt(day.content_text)
        if excerpt is None and day.content_json is not None:
            excerpt = _to_excerpt(str(day.content_json))
        if excerpt:
            score += min(0.42, len(excerpt) / 700)
    elif day.day_index in {2, 3}:
        if "commit" in kinds:
            score += 0.2
        if "diff" in kinds:
            score += 0.12
        if "test" in kinds:
            passed = day.tests_passed if isinstance(day.tests_passed, int) else 0
            failed = day.tests_failed if isinstance(day.tests_failed, int) else 0
            total = passed + failed
            ratio = (passed / total) if total > 0 else 0.5
            score += 0.08 + (0.15 * ratio)
    elif day.day_index == 4:
        transcript_chars = sum(
            len(_to_excerpt(_segment_text(segment), max_chars=200) or "")
            for segment in day.transcript_segments[:4]
        )
        if transcript_chars > 0:
            score += min(0.5, transcript_chars / 1200)
    return round(max(0.0, min(1.0, score)), 4)


def _recommendation_from_score(score: float) -> str:
    if score >= 0.85:
        return EVALUATION_RECOMMENDATION_STRONG_HIRE
    if score >= 0.7:
        return EVALUATION_RECOMMENDATION_HIRE
    if score >= 0.55:
        return EVALUATION_RECOMMENDATION_LEAN_HIRE
    return EVALUATION_RECOMMENDATION_NO_HIRE


__all__ = ["_recommendation_from_score", "_score_for_day"]
