"""Application module for evaluations services evaluations winoe report composer normalize service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATION_HIRE,
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
    EVALUATION_RECOMMENDATION_NO_HIRE,
    EVALUATION_RECOMMENDATION_STRONG_HIRE,
)

WINOE_REPORT_RECOMMENDATION_STRONG_SIGNAL = "strong_signal"
WINOE_REPORT_RECOMMENDATION_POSITIVE_SIGNAL = "positive_signal"
WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL = "mixed_signal"
WINOE_REPORT_RECOMMENDATION_LIMITED_SIGNAL = "limited_signal"

# Evaluation runs persist the internal storage enum, while the Winoe Report API
# surface uses the signal-oriented public vocabulary.
_STORED_TO_WINOE_RECOMMENDATION = {
    EVALUATION_RECOMMENDATION_STRONG_HIRE: WINOE_REPORT_RECOMMENDATION_STRONG_SIGNAL,
    EVALUATION_RECOMMENDATION_HIRE: WINOE_REPORT_RECOMMENDATION_POSITIVE_SIGNAL,
    EVALUATION_RECOMMENDATION_LEAN_HIRE: WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL,
    EVALUATION_RECOMMENDATION_NO_HIRE: WINOE_REPORT_RECOMMENDATION_LIMITED_SIGNAL,
}

_WINOE_RECOMMENDATIONS = {
    WINOE_REPORT_RECOMMENDATION_STRONG_SIGNAL,
    WINOE_REPORT_RECOMMENDATION_POSITIVE_SIGNAL,
    WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL,
    WINOE_REPORT_RECOMMENDATION_LIMITED_SIGNAL,
}


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_unit_interval(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    normalized = float(value)
    if normalized < 0 or normalized > 1:
        return None
    return round(normalized, 4)


def _normalize_recommendation(value: Any) -> str:
    """Translate stored evaluation recommendations into Winoe Report values."""
    if not isinstance(value, str):
        return WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL
    normalized = value.strip().lower()
    if normalized in _WINOE_RECOMMENDATIONS:
        return normalized
    if normalized in _STORED_TO_WINOE_RECOMMENDATION:
        return _STORED_TO_WINOE_RECOMMENDATION[normalized]
    return WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL


__all__ = [
    "WINOE_REPORT_RECOMMENDATION_LIMITED_SIGNAL",
    "WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL",
    "WINOE_REPORT_RECOMMENDATION_POSITIVE_SIGNAL",
    "WINOE_REPORT_RECOMMENDATION_STRONG_SIGNAL",
]
