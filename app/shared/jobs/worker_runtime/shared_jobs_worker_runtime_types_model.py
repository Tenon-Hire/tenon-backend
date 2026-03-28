"""Application module for jobs worker runtime types model workflows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

DEFAULT_LEASE_SECONDS = 300
DEFAULT_BASE_BACKOFF_SECONDS = 1
DEFAULT_MAX_BACKOFF_SECONDS = 60
DEFAULT_IDLE_SLEEP_SECONDS = 1.0

JobHandler = Callable[
    [dict[str, Any]],
    Awaitable[dict[str, Any] | None] | dict[str, Any] | None,
]


class PermanentJobError(Exception):
    """Signals an unrecoverable handler failure."""


def compute_backoff_seconds(
    attempt: int,
    *,
    base_seconds: int = DEFAULT_BASE_BACKOFF_SECONDS,
    max_seconds: int = DEFAULT_MAX_BACKOFF_SECONDS,
) -> int:
    """Compute backoff seconds."""
    if attempt < 1:
        return base_seconds
    return min(max_seconds, base_seconds * (2 ** (attempt - 1)))


__all__ = [
    "DEFAULT_BASE_BACKOFF_SECONDS",
    "DEFAULT_IDLE_SLEEP_SECONDS",
    "DEFAULT_LEASE_SECONDS",
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "JobHandler",
    "PermanentJobError",
    "compute_backoff_seconds",
]
