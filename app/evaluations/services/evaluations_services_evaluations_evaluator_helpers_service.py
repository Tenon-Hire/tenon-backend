from __future__ import annotations

import re
from typing import Any

_REPO_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _safe_repo_full_name(repo_full_name: str | None) -> str | None:
    if not isinstance(repo_full_name, str):
        return None
    normalized = repo_full_name.strip()
    if not _REPO_FULL_NAME_RE.match(normalized):
        return None
    return normalized


def _to_excerpt(value: str | None, *, max_chars: int = 280) -> str | None:
    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())
    if not compact:
        return None
    return compact[:max_chars]


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
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


def _segment_text(segment: dict[str, Any]) -> str | None:
    for key in ("text", "content", "excerpt"):
        value = segment.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


__all__ = [
    "_safe_int",
    "_safe_repo_full_name",
    "_segment_end_ms",
    "_segment_start_ms",
    "_segment_text",
    "_to_excerpt",
]
