from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


def test_storage_factory_resolves_s3_and_rejects_unsupported(monkeypatch):
    monkeypatch.setattr(settings.storage_media, "MEDIA_STORAGE_PROVIDER", "s3")
    monkeypatch.setattr(
        settings.storage_media, "MEDIA_S3_ENDPOINT", "https://s3.example"
    )
    monkeypatch.setattr(settings.storage_media, "MEDIA_S3_REGION", "us-east-1")
    monkeypatch.setattr(settings.storage_media, "MEDIA_S3_BUCKET", "bucket1")
    monkeypatch.setattr(settings.storage_media, "MEDIA_S3_ACCESS_KEY_ID", "akid")
    monkeypatch.setattr(settings.storage_media, "MEDIA_S3_SECRET_ACCESS_KEY", "secret")
    get_storage_media_provider.cache_clear()
    provider = get_storage_media_provider()
    assert isinstance(provider, S3StorageMediaProvider)

    monkeypatch.setattr(settings.storage_media, "MEDIA_STORAGE_PROVIDER", "nope")
    get_storage_media_provider.cache_clear()
    with pytest.raises(ValueError):
        get_storage_media_provider()
    get_storage_media_provider.cache_clear()
