from __future__ import annotations

from fastapi import HTTPException

from app.core.settings import settings
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    get_storage_media_provider,
    resolve_signed_url_ttl,
)
from app.services.media.keys import (
    build_recording_storage_key,
    parse_recording_public_id,
    recording_public_id,
)
from app.services.media.validation import validate_upload_input


def test_build_recording_storage_key_shape():
    key = build_recording_storage_key(
        candidate_session_id=12,
        task_id=34,
        extension="mp4",
        recording_uuid="abc123",
    )
    assert key == "candidate-sessions/12/tasks/34/recordings/abc123.mp4"


def test_recording_public_id_round_trip():
    public_id = recording_public_id(77)
    assert public_id == "rec_77"
    assert parse_recording_public_id(public_id) == 77
    assert parse_recording_public_id("88") == 88


def test_parse_recording_public_id_invalid():
    try:
        parse_recording_public_id("recording-1")
    except ValueError as exc:
        assert "recordingId" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError")


def test_validate_upload_input_success(monkeypatch):
    monkeypatch.setattr(
        settings.storage_media,
        "MEDIA_ALLOWED_CONTENT_TYPES",
        ["video/mp4", "video/webm"],
    )
    monkeypatch.setattr(
        settings.storage_media,
        "MEDIA_ALLOWED_EXTENSIONS",
        ["mp4", "webm"],
    )
    monkeypatch.setattr(settings.storage_media, "MEDIA_MAX_UPLOAD_BYTES", 10_000)

    payload = validate_upload_input(
        content_type="video/mp4; charset=utf-8",
        size_bytes=1_024,
        filename="demo.mp4",
    )
    assert payload.content_type == "video/mp4"
    assert payload.size_bytes == 1_024
    assert payload.extension == "mp4"


def test_validate_upload_input_rejects_invalid_values(monkeypatch):
    monkeypatch.setattr(
        settings.storage_media, "MEDIA_ALLOWED_CONTENT_TYPES", ["video/mp4"]
    )
    monkeypatch.setattr(settings.storage_media, "MEDIA_ALLOWED_EXTENSIONS", ["mp4"])
    monkeypatch.setattr(settings.storage_media, "MEDIA_MAX_UPLOAD_BYTES", 10)

    with_exception = None
    try:
        validate_upload_input(
            content_type="application/pdf",
            size_bytes=1,
            filename="x.pdf",
        )
    except HTTPException as exc:
        with_exception = exc
    assert with_exception is not None
    assert with_exception.status_code == 422

    with_exception = None
    try:
        validate_upload_input(
            content_type="video/mp4",
            size_bytes=11,
            filename="demo.mp4",
        )
    except HTTPException as exc:
        with_exception = exc
    assert with_exception is not None
    assert with_exception.status_code == 413
    assert getattr(with_exception, "error_code", None) == "REQUEST_TOO_LARGE"


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
    get_storage_media_provider.cache_clear()
    provider = get_storage_media_provider()
    assert isinstance(provider, FakeStorageMediaProvider)
    get_storage_media_provider.cache_clear()
