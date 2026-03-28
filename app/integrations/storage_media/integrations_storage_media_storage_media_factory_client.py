"""Application module for integrations storage media storage media factory client workflows."""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaProvider,
    clamp_expires_seconds,
)
from app.integrations.storage_media.integrations_storage_media_storage_media_fake_provider_client import (
    FakeStorageMediaProvider,
)
from app.integrations.storage_media.integrations_storage_media_storage_media_s3_provider_client import (
    S3StorageMediaProvider,
)


@lru_cache
def get_storage_media_provider() -> StorageMediaProvider:
    """Return the configured media storage provider."""
    cfg = settings.storage_media
    provider_name = (cfg.MEDIA_STORAGE_PROVIDER or "fake").strip().lower()
    if provider_name == "fake":
        return FakeStorageMediaProvider()
    if provider_name == "s3":
        return S3StorageMediaProvider(
            endpoint=cfg.MEDIA_S3_ENDPOINT,
            region=cfg.MEDIA_S3_REGION,
            bucket=cfg.MEDIA_S3_BUCKET,
            access_key_id=cfg.MEDIA_S3_ACCESS_KEY_ID,
            secret_access_key=cfg.MEDIA_S3_SECRET_ACCESS_KEY,
            session_token=cfg.MEDIA_S3_SESSION_TOKEN,
            use_path_style=cfg.MEDIA_S3_USE_PATH_STYLE,
        )
    raise ValueError(f"Unsupported media storage provider: {provider_name}")


def resolve_signed_url_ttl(expires_seconds: int | None = None) -> int:
    """Clamp a requested TTL to configured media bounds."""
    cfg = settings.storage_media
    if expires_seconds is not None:
        requested = expires_seconds
    else:
        requested = int(
            cfg.MEDIA_SIGNED_URL_EXPIRES_SECONDS or cfg.SIGNED_URL_EXPIRY_SECONDS
        )
    return clamp_expires_seconds(
        requested,
        min_seconds=cfg.MEDIA_SIGNED_URL_MIN_SECONDS,
        max_seconds=cfg.MEDIA_SIGNED_URL_MAX_SECONDS,
    )


__all__ = ["get_storage_media_provider", "resolve_signed_url_ttl"]
