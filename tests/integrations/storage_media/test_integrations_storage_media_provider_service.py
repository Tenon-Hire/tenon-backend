from __future__ import annotations

from app.config import settings
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    get_storage_media_provider,
    resolve_signed_url_ttl,
)


def test_resolve_signed_url_ttl_clamps(monkeypatch):
    monkeypatch.setattr(settings.storage_media, "MEDIA_SIGNED_URL_EXPIRES_SECONDS", 900)
    monkeypatch.setattr(settings.storage_media, "MEDIA_SIGNED_URL_MIN_SECONDS", 60)
    monkeypatch.setattr(settings.storage_media, "MEDIA_SIGNED_URL_MAX_SECONDS", 1200)
    assert resolve_signed_url_ttl() == 900
    assert resolve_signed_url_ttl(1) == 60
    assert resolve_signed_url_ttl(5_000) == 1200


def test_fake_provider_generates_signed_urls():
    provider = FakeStorageMediaProvider(base_url="https://fake.example")
    upload_url = provider.create_signed_upload_url(
        "candidate-sessions/1/tasks/4/recordings/abc.mp4",
        "video/mp4",
        1234,
        900,
    )
    download_url = provider.create_signed_download_url(
        "candidate-sessions/1/tasks/4/recordings/abc.mp4",
        900,
    )
    assert upload_url.startswith("https://fake.example/upload?")
    assert "expiresIn=900" in upload_url
    assert "sig=" in upload_url
    assert download_url.startswith("https://fake.example/download?")
    assert "expiresIn=900" in download_url


def test_storage_provider_factory_resolves_fake(monkeypatch):
    monkeypatch.setattr(settings.storage_media, "MEDIA_STORAGE_PROVIDER", "fake")
    monkeypatch.setattr(
        settings.storage_media,
        "MEDIA_FAKE_BASE_URL",
        "https://media.example.test/api/recordings/storage/fake",
    )
    get_storage_media_provider.cache_clear()
    provider = get_storage_media_provider()
    assert isinstance(provider, FakeStorageMediaProvider)
    assert provider.create_signed_download_url(
        "candidate-sessions/1/tasks/4/recordings/abc.mp4",
        900,
    ).startswith("https://media.example.test/api/recordings/storage/fake/download?")
    get_storage_media_provider.cache_clear()
