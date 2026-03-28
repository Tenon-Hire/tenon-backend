"""Application module for http dependencies storage media utils workflows."""

from __future__ import annotations

from app.integrations.storage_media import (
    StorageMediaProvider,
    get_storage_media_provider,
)


def get_media_storage_provider() -> StorageMediaProvider:
    """Dependency wrapper for media storage provider injection."""
    return get_storage_media_provider()


__all__ = ["get_media_storage_provider"]
