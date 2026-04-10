"""Application module for trials schemas trials ai values schema workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.trials.constants.trials_constants_trials_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.trials.schemas.trials_schemas_trials_limits_schema import (
    _ALLOWED_AI_EVAL_DAY_KEYS,
    MAX_AI_NOTICE_TEXT_CHARS,
    MAX_AI_NOTICE_VERSION_CHARS,
)


def normalize_eval_enabled_by_day(
    value: Any,
    *,
    strict: bool,
) -> dict[str, bool] | None:
    """Normalize eval enabled by day."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        if strict:
            raise ValueError("evalEnabledByDay must be an object mapping day to bool")
        return None
    normalized: dict[str, bool] = {}
    for raw_key, raw_value in value.items():
        day_key = str(raw_key).strip()
        if day_key not in _ALLOWED_AI_EVAL_DAY_KEYS:
            if strict:
                allowed = ", ".join(sorted(_ALLOWED_AI_EVAL_DAY_KEYS))
                raise ValueError(f"evalEnabledByDay day keys must be one of: {allowed}")
            continue
        if not isinstance(raw_value, bool):
            if strict:
                raise ValueError(
                    f"evalEnabledByDay[{day_key}] must be a boolean true/false value"
                )
            continue
        normalized[day_key] = raw_value
    return normalized


def _coerce_notice_value(value: Any, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        return None
    return normalized


def resolve_trial_ai_fields(
    *,
    notice_version: Any,
    notice_text: Any,
    eval_enabled_by_day: Any,
    fallback_notice_version: Any = None,
    fallback_notice_text: Any = None,
    fallback_eval_enabled_by_day: Any = None,
) -> tuple[str, str, dict[str, bool]]:
    """Resolve trial ai fields."""
    resolved_notice_version = (
        _coerce_notice_value(notice_version, max_length=MAX_AI_NOTICE_VERSION_CHARS)
        or _coerce_notice_value(
            fallback_notice_version,
            max_length=MAX_AI_NOTICE_VERSION_CHARS,
        )
        or AI_NOTICE_DEFAULT_VERSION
    )
    resolved_notice_text = (
        _coerce_notice_value(notice_text, max_length=MAX_AI_NOTICE_TEXT_CHARS)
        or _coerce_notice_value(
            fallback_notice_text, max_length=MAX_AI_NOTICE_TEXT_CHARS
        )
        or AI_NOTICE_DEFAULT_TEXT
    )
    resolved_eval = default_ai_eval_enabled_by_day()
    fallback_eval = normalize_eval_enabled_by_day(
        fallback_eval_enabled_by_day, strict=False
    )
    if fallback_eval is not None:
        resolved_eval.update(fallback_eval)
    incoming_eval = normalize_eval_enabled_by_day(eval_enabled_by_day, strict=False)
    if incoming_eval is not None:
        resolved_eval.update(incoming_eval)
    return resolved_notice_version, resolved_notice_text, resolved_eval


__all__ = ["normalize_eval_enabled_by_day", "resolve_trial_ai_fields"]
