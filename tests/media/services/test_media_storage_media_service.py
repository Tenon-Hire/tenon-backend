from __future__ import annotations

from fastapi import HTTPException

from app.config import settings
from app.media.services.media_services_media_keys_service import (
    build_recording_storage_key,
    parse_recording_public_id,
    recording_public_id,
)
from app.media.services.media_services_media_validation_service import (
    validate_upload_input,
)


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
        ["video/mp4"],
    )
    monkeypatch.setattr(
        settings.storage_media,
        "MEDIA_ALLOWED_EXTENSIONS",
        ["mp4"],
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


def test_validate_upload_input_rejects_mov_uploads(monkeypatch):
    monkeypatch.setattr(
        settings.storage_media,
        "MEDIA_ALLOWED_CONTENT_TYPES",
        ["video/mp4"],
    )
    monkeypatch.setattr(settings.storage_media, "MEDIA_ALLOWED_EXTENSIONS", ["mp4"])
    monkeypatch.setattr(settings.storage_media, "MEDIA_MAX_UPLOAD_BYTES", 10_000)

    with_exception = None
    try:
        validate_upload_input(
            content_type="video/quicktime",
            size_bytes=1_024,
            filename="demo.mov",
        )
    except HTTPException as exc:
        with_exception = exc

    assert with_exception is not None
    assert with_exception.status_code == 422
    assert with_exception.detail == "Unsupported contentType"


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
