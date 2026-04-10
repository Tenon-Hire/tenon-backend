"""Application module for evaluations services evaluations winoe report composer normalize service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
    EVALUATION_RECOMMENDATIONS,
)


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
    if not isinstance(value, str):
        return EVALUATION_RECOMMENDATION_LEAN_HIRE
    normalized = value.strip().lower()
    if normalized not in EVALUATION_RECOMMENDATIONS:
        return EVALUATION_RECOMMENDATION_LEAN_HIRE
    return normalized
