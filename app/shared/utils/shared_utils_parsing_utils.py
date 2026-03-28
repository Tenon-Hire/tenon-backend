"""Application module for utils parsing utils workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def parse_positive_int(value: Any, *, strip_strings: bool = False) -> int | None:
    """Parse positive int."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        raw = value.strip() if strip_strings else value
        if raw.isdigit():
            parsed = int(raw)
            return parsed if parsed > 0 else None
    return None


def parse_iso_datetime(value: Any) -> datetime | None:
    """Parse iso datetime."""
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = ["parse_iso_datetime", "parse_positive_int"]
