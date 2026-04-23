"""Application module for evaluations repositories evaluations validation scalars repository workflows."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATIONS,
    EVALUATION_RUN_STATUSES,
)

WINOE_REPORT_RECOMMENDATION_TO_STORAGE = {
    "strong_signal": "strong_hire",
    "positive_signal": "hire",
    "mixed_signal": "lean_hire",
    "limited_signal": "no_hire",
}


def normalize_non_empty_str(value: Any, *, field_name: str) -> str:
    """Normalize non empty str."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def normalize_optional_non_empty_str(value: Any, *, field_name: str) -> str | None:
    """Normalize optional non empty str."""
    if value is None:
        return None
    return normalize_non_empty_str(value, field_name=field_name)


def normalize_datetime(value: datetime | None, *, field_name: str, default_now: bool):
    """Normalize datetime."""
    if value is None:
        return datetime.now(UTC).replace(microsecond=0) if default_now else None
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime.")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def normalize_status(status: str) -> str:
    """Normalize status."""
    normalized = (status or "").strip().lower()
    if normalized not in EVALUATION_RUN_STATUSES:
        raise ValueError(f"invalid evaluation run status: {status}")
    return normalized


def coerce_object(
    value: Mapping[str, Any] | None, *, field_name: str
) -> dict[str, Any] | None:
    """Execute coerce object."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object when provided.")
    return dict(value)


def coerce_unit_interval_score(value: Any, *, field_name: str, required: bool = False):
    """Execute coerce unit interval score."""
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required.")
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be numeric when provided.")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field_name} must be finite.")
    if normalized < 0.0 or normalized > 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1.")
    return normalized


def coerce_recommendation(value: Any, *, required: bool = False) -> str | None:
    """Execute coerce recommendation."""
    if value is None:
        if required:
            raise ValueError("recommendation is required.")
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("recommendation must be a non-empty string when provided.")
    normalized = value.strip().lower()
    normalized = WINOE_REPORT_RECOMMENDATION_TO_STORAGE.get(normalized, normalized)
    if normalized not in EVALUATION_RECOMMENDATIONS:
        raise ValueError(f"invalid recommendation: {value}")
    return normalized


def coerce_day_index(value: Any, *, field_path: str) -> int:
    """Execute coerce day index."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_path} must be an integer.")
    if value < 1 or value > 5:
        raise ValueError(f"{field_path} must be between 1 and 5.")
    return value


def coerce_score(value: Any, *, field_path: str) -> float:
    """Execute coerce score."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_path} must be numeric.")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field_path} must be finite.")
    return normalized


def coerce_rubric_results_json(value: Any, *, field_path: str) -> dict[str, Any]:
    """Execute coerce rubric results json."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_path} must be an object.")
    return dict(value)
