"""Application module for jobs handlers transcribe recording helpers handler workflows."""

from __future__ import annotations

from typing import Any


def _sanitize_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:512]


def _coerce_non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    if isinstance(value, str) and value.strip().isdigit():
        return max(0, int(value.strip()))
    return 0


def _normalize_segments(raw_segments: Any) -> list[dict[str, object]]:
    if not isinstance(raw_segments, list):
        return []
    normalized: list[dict[str, object]] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        normalized.append(
            {
                "startMs": _coerce_non_negative_int(item.get("startMs")),
                "endMs": _coerce_non_negative_int(item.get("endMs")),
                "text": text.strip(),
            }
        )
    return normalized


__all__ = ["_normalize_segments", "_sanitize_error"]
