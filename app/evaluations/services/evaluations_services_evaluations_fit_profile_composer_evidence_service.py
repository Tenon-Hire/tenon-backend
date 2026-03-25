from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _sanitize_evidence(pointer: Any) -> dict[str, Any] | None:
    if not isinstance(pointer, Mapping):
        return None
    kind_raw = pointer.get("kind")
    if not isinstance(kind_raw, str) or not kind_raw.strip():
        return None

    sanitized: dict[str, Any] = {"kind": kind_raw.strip()}
    for key in ("ref", "url", "excerpt"):
        value = pointer.get(key)
        if isinstance(value, str) and value.strip():
            sanitized[key] = value.strip()

    if sanitized["kind"] == "transcript":
        start_ms = pointer.get("startMs")
        end_ms = pointer.get("endMs")
        if isinstance(start_ms, int) and start_ms >= 0:
            sanitized["startMs"] = start_ms
        if isinstance(end_ms, int) and end_ms >= 0:
            sanitized["endMs"] = end_ms
    return sanitized


def _human_review_day_from_raw(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    day_index = value.get("dayIndex")
    status_value = value.get("status")
    reason_value = value.get("reason")
    if isinstance(day_index, bool) or not isinstance(day_index, int):
        return None
    if day_index < 1 or day_index > 5:
        return None
    if not isinstance(status_value, str) or status_value != "human_review_required":
        return None
    if not isinstance(reason_value, str) or not reason_value.strip():
        return None
    return {
        "dayIndex": day_index,
        "score": None,
        "rubricBreakdown": {},
        "evidence": [],
        "status": status_value,
        "reason": reason_value.strip(),
    }
