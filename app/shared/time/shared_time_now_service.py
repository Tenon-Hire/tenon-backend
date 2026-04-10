"""Shared clock helpers for runtime and contract-live validation."""

from __future__ import annotations

import os
from datetime import UTC, datetime

_TEST_NOW_ENV_KEYS = (
    "WINOE_TEST_NOW_UTC",
    "CONTRACT_LIVE_FAKE_TIME_UTC",
    "CONTRACT_LIVE_FAKE_TIME",
)
_NAIVE_TEST_NOW_FORMATS = ("%Y-%m-%d %H:%M:%S",)


def _raw_test_now() -> str | None:
    for key in _TEST_NOW_ENV_KEYS:
        value = (os.environ.get(key) or "").strip()
        if value:
            return value
    return None


def _parse_test_now(raw: str | None) -> datetime | None:
    if not raw:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    normalized = candidate[:-1] + "+00:00" if candidate.endswith("Z") else candidate
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None
        for fmt in _NAIVE_TEST_NOW_FORMATS:
            try:
                parsed = datetime.strptime(candidate, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def utcnow() -> datetime:
    """Return the shared current UTC time, honoring contract-live overrides."""
    parsed = _parse_test_now(_raw_test_now())
    return parsed if parsed is not None else datetime.now(UTC)


__all__ = ["utcnow"]
