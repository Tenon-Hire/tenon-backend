"""Application module for auth rate limit rules utils workflows."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from fastapi import Request

from app.config import settings
from app.shared.utils.shared_utils_env_utils import is_local_or_test

DEFAULT_RATE_LIMIT_DETAIL = "Too many requests. Please slow down."


@dataclass(frozen=True)
class RateLimitRule:
    """Represent rate limit rule data and behavior."""

    limit: int
    window_seconds: float


def rate_limit_enabled() -> bool:
    """Execute rate limit enabled."""
    if settings.RATE_LIMIT_ENABLED is not None:
        return bool(settings.RATE_LIMIT_ENABLED)
    return not is_local_or_test()


def _client_host(request: Request) -> str | None:
    client = getattr(request, "client", None)
    if client and getattr(client, "host", None):
        return str(client.host)
    return None


def client_id(request: Request) -> str:
    """Execute client id."""
    return _client_host(request) or "unknown"


def hash_value(value: str) -> str:
    """Execute hash value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def rate_limit_key(*parts: str) -> str:
    """Execute rate limit key."""
    return ":".join(part for part in parts if part)


__all__ = [
    "DEFAULT_RATE_LIMIT_DETAIL",
    "RateLimitRule",
    "rate_limit_enabled",
    "client_id",
    "hash_value",
    "rate_limit_key",
]
