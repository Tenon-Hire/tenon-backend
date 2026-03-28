"""Application module for evaluations services evaluations fit profile pipeline parse service workflows."""

from __future__ import annotations

import json
from typing import Any

from app.shared.utils.shared_utils_parsing_utils import (
    parse_positive_int as _parse_positive_int_value,
)


def _parse_positive_int(value: Any) -> int | None:
    return _parse_positive_int_value(value)


def _normalize_day_toggles(raw: Any) -> tuple[list[int], list[int]]:
    disabled: list[int] = []
    enabled: list[int] = []
    toggles = raw if isinstance(raw, dict) else {}
    for day in range(1, 6):
        if toggles.get(str(day)) is False:
            disabled.append(day)
        else:
            enabled.append(day)
    return enabled, disabled


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _parse_diff_summary(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _segment_text(segment: dict[str, Any]) -> str | None:
    for key in ("text", "content", "excerpt"):
        value = segment.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _segment_start_ms(segment: dict[str, Any]) -> int | None:
    for key in ("startMs", "start_ms", "start"):
        value = _safe_int(segment.get(key))
        if value is not None:
            return max(0, value)
    return None


def _segment_end_ms(segment: dict[str, Any]) -> int | None:
    for key in ("endMs", "end_ms", "end"):
        value = _safe_int(segment.get(key))
        if value is not None:
            return max(0, value)
    return None


def _normalize_transcript_segments(raw_segments: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_segments, list):
        return []
    normalized: list[dict[str, Any]] = []
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            continue
        start_ms = _segment_start_ms(raw_segment)
        end_ms = _segment_end_ms(raw_segment)
        if start_ms is None or end_ms is None:
            continue
        segment: dict[str, Any] = {"startMs": start_ms, "endMs": max(start_ms, end_ms)}
        text = _segment_text(raw_segment)
        if text is not None:
            segment["text"] = text
        normalized.append(segment)
    return normalized


__all__ = [
    "_normalize_day_toggles",
    "_normalize_transcript_segments",
    "_parse_diff_summary",
    "_parse_positive_int",
    "_safe_int",
    "_segment_end_ms",
    "_segment_start_ms",
    "_segment_text",
]
