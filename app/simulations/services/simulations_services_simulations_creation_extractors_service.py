"""Application module for simulations services simulations creation extractors service workflows."""

from __future__ import annotations

from datetime import time
from typing import Any

from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    normalize_eval_enabled_by_day,
)


def extract_company_context(payload: Any) -> dict[str, Any] | None:
    """Extract company context."""
    raw_company_context = getattr(
        payload, "company_context", getattr(payload, "companyContext", None)
    )
    if raw_company_context is None:
        return None
    if hasattr(raw_company_context, "model_dump"):
        return raw_company_context.model_dump(by_alias=True, exclude_none=True)
    if isinstance(raw_company_context, dict):
        return dict(raw_company_context)
    return None


def extract_ai_fields(
    payload: Any,
) -> tuple[str | None, str | None, dict[str, bool] | None]:
    """Extract ai fields."""
    raw_ai = getattr(payload, "ai", None)
    if raw_ai is None:
        return None, None, None
    if isinstance(raw_ai, dict):
        notice_version = raw_ai.get("noticeVersion")
        notice_text = raw_ai.get("noticeText")
        eval_by_day = raw_ai.get("evalEnabledByDay")
    else:
        notice_version = getattr(raw_ai, "notice_version", None) or getattr(
            raw_ai, "noticeVersion", None
        )
        notice_text = getattr(raw_ai, "notice_text", None) or getattr(
            raw_ai, "noticeText", None
        )
        eval_by_day = getattr(raw_ai, "eval_enabled_by_day", None) or getattr(
            raw_ai, "evalEnabledByDay", None
        )
    return (
        notice_version,
        notice_text,
        normalize_eval_enabled_by_day(eval_by_day, strict=False),
    )


def extract_day_window_config(
    payload: Any,
) -> tuple[time, time, bool, dict[str, dict[str, str]] | None]:
    """Extract day window config."""
    day_window_start_local = getattr(payload, "dayWindowStartLocal", None) or time(
        hour=9, minute=0
    )
    day_window_end_local = getattr(payload, "dayWindowEndLocal", None) or time(
        hour=17, minute=0
    )
    overrides_enabled = bool(getattr(payload, "dayWindowOverridesEnabled", False))
    raw_overrides = getattr(payload, "dayWindowOverrides", None)
    if raw_overrides is None:
        return day_window_start_local, day_window_end_local, overrides_enabled, None
    normalized_overrides: dict[str, dict[str, str]] = {}
    for raw_day, raw_window in raw_overrides.items():
        if hasattr(raw_window, "model_dump"):
            serialized = raw_window.model_dump(by_alias=True)
        elif isinstance(raw_window, dict):
            serialized = dict(raw_window)
        else:
            continue
        normalized_overrides[str(raw_day)] = {
            "startLocal": str(serialized.get("startLocal")),
            "endLocal": str(serialized.get("endLocal")),
        }
    return (
        day_window_start_local,
        day_window_end_local,
        overrides_enabled,
        normalized_overrides or None,
    )
