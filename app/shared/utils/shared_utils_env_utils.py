"""Environment helpers shared across the app."""

from __future__ import annotations

import os

from app.config import settings


def env_name() -> str:
    """Normalized environment name (lowercase)."""
    configured = getattr(settings, "ENV", None)
    if configured:
        return str(configured).lower()
    return str(os.getenv("WINOE_ENV") or os.getenv("ENV") or "local").lower()


def is_local_or_test() -> bool:
    """Return True when running in local or test environments."""
    return env_name() in {"local", "test"}


def is_prod() -> bool:
    """Return True when running in production."""
    return env_name() == "prod"
