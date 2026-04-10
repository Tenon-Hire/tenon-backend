"""Application module for config defaults config workflows."""

from __future__ import annotations

DEFAULT_CLAIM_NAMESPACE = "https://winoe.ai"


def normalize_sync_url(url: str) -> str:
    """Normalize postgres:// -> postgresql:// for sync DSNs."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def to_async_url(url: str) -> str:
    """Convert sync URLs to async driver URLs when needed."""
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///") and "+aiosqlite" not in url:
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url
