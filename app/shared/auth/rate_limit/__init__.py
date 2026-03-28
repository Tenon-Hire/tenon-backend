"""Application module for init workflows."""

from __future__ import annotations

from app.config import settings

from .shared_auth_rate_limit_limiter_utils import RateLimiter
from .shared_auth_rate_limit_rules_utils import (
    DEFAULT_RATE_LIMIT_DETAIL,
    RateLimitRule,
    client_id,
    hash_value,
    rate_limit_enabled,
    rate_limit_key,
)

limiter = RateLimiter()

__all__ = [
    "DEFAULT_RATE_LIMIT_DETAIL",
    "RateLimitRule",
    "RateLimiter",
    "rate_limit_enabled",
    "client_id",
    "hash_value",
    "rate_limit_key",
    "limiter",
    "settings",
]
