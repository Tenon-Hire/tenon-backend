"""Application module for evaluations services evaluations runs coercion service workflows."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATIONS,
)
from app.evaluations.services.evaluations_services_evaluations_runs_validation_service import (
    EvaluationRunStateError,
)


def coerce_unit_interval_score(
    value: Any, *, field_name: str, required: bool
) -> float | None:
    """Execute coerce unit interval score."""
    if value is None:
        if required:
            raise EvaluationRunStateError(f"{field_name} is required.")
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise EvaluationRunStateError(f"{field_name} must be numeric.")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise EvaluationRunStateError(f"{field_name} must be finite.")
    if normalized < 0 or normalized > 1:
        raise EvaluationRunStateError(f"{field_name} must be between 0 and 1.")
    return normalized


def coerce_recommendation(value: Any, *, required: bool) -> str | None:
    """Execute coerce recommendation."""
    if value is None:
        if required:
            raise EvaluationRunStateError("recommendation is required.")
        return None
    if not isinstance(value, str) or not value.strip():
        raise EvaluationRunStateError("recommendation must be a non-empty string.")
    normalized = value.strip().lower()
    if normalized not in EVALUATION_RECOMMENDATIONS:
        raise EvaluationRunStateError(f"invalid recommendation: {value}")
    return normalized


def coerce_raw_report_json(raw_report_json: Any) -> dict[str, Any] | None:
    """Execute coerce raw report json."""
    if raw_report_json is None:
        return None
    if not isinstance(raw_report_json, Mapping):
        raise EvaluationRunStateError("raw_report_json must be an object.")
    return dict(raw_report_json)


__all__ = [
    "coerce_raw_report_json",
    "coerce_recommendation",
    "coerce_unit_interval_score",
]
