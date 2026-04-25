"""Application module for trials services trials candidates compare formatting service workflows."""

from __future__ import annotations

from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATION_HIRE,
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
    EVALUATION_RECOMMENDATION_NO_HIRE,
    EVALUATION_RECOMMENDATION_STRONG_HIRE,
    EVALUATION_RECOMMENDATIONS,
)
from app.trials.schemas.trials_schemas_trials_compare_schema import (
    PublicCompareRecommendation,
)

_PUBLIC_RECOMMENDATIONS: set[PublicCompareRecommendation] = {
    "strong_signal",
    "positive_signal",
    "mixed_signal",
    "limited_signal",
}

_STORED_TO_PUBLIC_RECOMMENDATION = {
    EVALUATION_RECOMMENDATION_STRONG_HIRE: "strong_signal",
    EVALUATION_RECOMMENDATION_HIRE: "positive_signal",
    EVALUATION_RECOMMENDATION_LEAN_HIRE: "mixed_signal",
    EVALUATION_RECOMMENDATION_NO_HIRE: "limited_signal",
}


def anonymized_candidate_label(position: int) -> str:
    # 0 -> A, 25 -> Z, 26 -> AA, 27 -> AB
    """Execute anonymized candidate label."""
    if position < 0:
        position = 0
    encoded: list[str] = []
    value = position
    while True:
        value, remainder = divmod(value, 26)
        encoded.append(chr(ord("A") + remainder))
        if value == 0:
            break
        value -= 1
    return f"Candidate {''.join(reversed(encoded))}"


def display_name(candidate_name: Any, *, position: int) -> str:
    """Execute display name."""
    if isinstance(candidate_name, str):
        normalized = candidate_name.strip()
        if normalized:
            return normalized
    return anonymized_candidate_label(position)


def normalize_score(value: Any) -> float | None:
    """Normalize score."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    normalized = float(value)
    return normalized if 0 <= normalized <= 1 else None


def normalize_recommendation(value: Any) -> PublicCompareRecommendation | None:
    """Normalize recommendation."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in _PUBLIC_RECOMMENDATIONS:
        return normalized
    if normalized in _STORED_TO_PUBLIC_RECOMMENDATION:
        return _STORED_TO_PUBLIC_RECOMMENDATION[normalized]
    if normalized not in EVALUATION_RECOMMENDATIONS:
        return None
    return None


__all__ = [
    "anonymized_candidate_label",
    "display_name",
    "normalize_recommendation",
    "normalize_score",
]
