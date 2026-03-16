from __future__ import annotations

from urllib.error import HTTPError

import pytest
from fastapi import HTTPException

import app.integrations.storage_media.s3_provider as s3_module
from app.core.settings import settings
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    S3StorageMediaProvider,
    ensure_safe_storage_key,
    get_storage_media_provider,
)
from app.integrations.storage_media.base import StorageMediaError
from app.services.media.keys import (
    build_recording_storage_key,
    normalize_extension,
    parse_recording_public_id,
)
from app.services.media.validation import validate_upload_input


def _build_s3_provider(*, use_path_style: bool = True) -> S3StorageMediaProvider:
    return S3StorageMediaProvider(
        endpoint="https://storage.example.com:9000/base",
        region="us-east-1",
        bucket="media-bucket",
        access_key_id="AKIA_TEST",
        secret_access_key="secret_test_key",
        use_path_style=use_path_style,
    )


def test_ensure_safe_storage_key_rejects_invalid_patterns():
    for key in ("", "/absolute/path.mp4", "path\\with\\backslash.mp4", "a//b.mp4"):
        with pytest.raises(StorageMediaError):
            ensure_safe_storage_key(key)
    with pytest.raises(StorageMediaError):
        ensure_safe_storage_key("a/./b.mp4")
    with pytest.raises(StorageMediaError):
        ensure_safe_storage_key("a/../b.mp4")
    with pytest.raises(StorageMediaError):
        ensure_safe_storage_key("a/b?c.mp4")


def test_fake_provider_set_and_delete_object_metadata():
    provider = FakeStorageMediaProvider()
    key = "candidate-sessions/1/tasks/2/recordings/demo.mp4"
    provider.set_object_metadata(key, content_type="video/mp4", size_bytes=99)
    assert provider.get_object_metadata(key) is not None
    provider.delete_object(key)
    assert provider.get_object_metadata(key) is None


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


def test_keys_validation_edge_cases():
    with pytest.raises(ValueError):
        parse_recording_public_id("rec_0")
    with pytest.raises(ValueError):
        normalize_extension("")
    with pytest.raises(ValueError):
        normalize_extension("m-p4")
    with pytest.raises(ValueError):
        build_recording_storage_key(
            candidate_session_id=0,
            task_id=1,
            extension="mp4",
        )


def test_upload_validation_extension_edge_cases(monkeypatch):
    monkeypatch.setattr(
        settings.storage_media, "MEDIA_ALLOWED_CONTENT_TYPES", ["video/mp4"]
    )
    monkeypatch.setattr(settings.storage_media, "MEDIA_ALLOWED_EXTENSIONS", ["mp4"])
    monkeypatch.setattr(settings.storage_media, "MEDIA_MAX_UPLOAD_BYTES", 9999)

    with pytest.raises(HTTPException):
        validate_upload_input(
            content_type="video/mp4",
            size_bytes=0,
            filename="demo.mp4",
        )
    with pytest.raises(HTTPException):
        validate_upload_input(
            content_type="video/mp4",
            size_bytes=1,
            filename="demo",
        )
    with pytest.raises(HTTPException):
        validate_upload_input(
            content_type="video/mp4",
            size_bytes=1,
            filename="demo.webm",
        )


def test_upload_validation_without_filename_edges(monkeypatch):
    monkeypatch.setattr(
        settings.storage_media,
        "MEDIA_ALLOWED_CONTENT_TYPES",
        ["video/mp4", "video/x-matroska"],
    )
    monkeypatch.setattr(settings.storage_media, "MEDIA_ALLOWED_EXTENSIONS", ["mp4"])
    monkeypatch.setattr(settings.storage_media, "MEDIA_MAX_UPLOAD_BYTES", 9999)

    inferred = validate_upload_input(
        content_type="video/mp4",
        size_bytes=12,
        filename=None,
    )
    assert inferred.extension == "mp4"

    with pytest.raises(HTTPException):
        validate_upload_input(
            content_type="video/x-matroska",
            size_bytes=12,
            filename=None,
        )

    monkeypatch.setattr(settings.storage_media, "MEDIA_ALLOWED_EXTENSIONS", ["webm"])
    with pytest.raises(HTTPException):
        validate_upload_input(
            content_type="video/mp4",
            size_bytes=12,
            filename=None,
        )


def test_s3_provider_signing_and_validation_edges():
    provider = _build_s3_provider()
    upload_url = provider.create_signed_upload_url(
        "candidate-sessions/1/tasks/4/recordings/demo.mp4",
        "video/mp4",
        100,
        900,
    )
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in upload_url
    assert "X-Amz-SignedHeaders=content-type%3Bhost" in upload_url
    assert (
        "/base/media-bucket/candidate-sessions/1/tasks/4/recordings/demo.mp4"
        in upload_url
    )

    download_url = provider.create_signed_download_url(
        "candidate-sessions/1/tasks/4/recordings/demo.mp4",
        900,
    )
    assert "X-Amz-SignedHeaders=host" in download_url

    with pytest.raises(StorageMediaError):
        provider.create_signed_download_url(
            "candidate-sessions/1/tasks/4/recordings/demo.mp4",
            0,
        )
    with pytest.raises(StorageMediaError):
        provider.create_signed_upload_url(
            "candidate-sessions/1/tasks/4/recordings/demo.mp4",
            "",
            10,
            900,
        )


def test_s3_provider_virtual_host_style():
    provider = _build_s3_provider(use_path_style=False)
    download_url = provider.create_signed_download_url(
        "candidate-sessions/2/tasks/6/recordings/demo.webm",
        120,
    )
    assert download_url.startswith("https://media-bucket.storage.example.com:9000/")
    assert "/base/candidate-sessions/2/tasks/6/recordings/demo.webm" in download_url


def test_s3_provider_get_object_metadata_success(monkeypatch):
    provider = _build_s3_provider()

    class _Response:
        def __init__(self):
            self.headers = {
                "Content-Length": "321",
                "Content-Type": "video/mp4; charset=utf-8",
            }

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    monkeypatch.setattr(s3_module, "urlopen", lambda request, timeout: _Response())
    metadata = provider.get_object_metadata(
        "candidate-sessions/3/tasks/7/recordings/object.mp4"
    )
    assert metadata is not None
    assert metadata.size_bytes == 321
    assert metadata.content_type == "video/mp4"


def test_s3_provider_get_object_metadata_404_returns_none(monkeypatch):
    provider = _build_s3_provider()

    def _raise_404(request, timeout):
        del request, timeout
        raise HTTPError(
            url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
        )

    monkeypatch.setattr(s3_module, "urlopen", _raise_404)
    metadata = provider.get_object_metadata(
        "candidate-sessions/3/tasks/7/recordings/missing.mp4"
    )
    assert metadata is None


def test_s3_provider_delete_object_handles_success_and_missing(monkeypatch):
    provider = _build_s3_provider()

    class _DeleteResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    monkeypatch.setattr(
        s3_module, "urlopen", lambda request, timeout: _DeleteResponse()
    )
    provider.delete_object("candidate-sessions/3/tasks/7/recordings/object.mp4")

    def _raise_404(request, timeout):
        del request, timeout
        raise HTTPError(
            url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
        )

    monkeypatch.setattr(s3_module, "urlopen", _raise_404)
    provider.delete_object("candidate-sessions/3/tasks/7/recordings/missing.mp4")


def test_s3_provider_delete_object_error_paths(monkeypatch):
    provider = _build_s3_provider()

    def _raise_500(request, timeout):
        del request, timeout
        raise HTTPError(
            url="https://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(s3_module, "urlopen", _raise_500)
    with pytest.raises(StorageMediaError):
        provider.delete_object("candidate-sessions/3/tasks/7/recordings/object.mp4")

    def _raise_oserror(request, timeout):
        del request, timeout
        raise OSError("network down")

    monkeypatch.setattr(s3_module, "urlopen", _raise_oserror)
    with pytest.raises(StorageMediaError):
        provider.delete_object("candidate-sessions/3/tasks/7/recordings/object.mp4")


def test_s3_provider_get_object_metadata_error_paths(monkeypatch):
    provider = _build_s3_provider()

    class _MissingLengthResponse:
        def __init__(self):
            self.headers = {"Content-Type": "video/mp4"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    monkeypatch.setattr(
        s3_module, "urlopen", lambda request, timeout: _MissingLengthResponse()
    )
    with pytest.raises(StorageMediaError):
        provider.get_object_metadata("candidate-sessions/9/tasks/9/recordings/demo.mp4")

    class _InvalidLengthResponse:
        def __init__(self):
            self.headers = {"Content-Length": "abc", "Content-Type": "video/mp4"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    monkeypatch.setattr(
        s3_module, "urlopen", lambda request, timeout: _InvalidLengthResponse()
    )
    with pytest.raises(StorageMediaError):
        provider.get_object_metadata("candidate-sessions/9/tasks/9/recordings/demo.mp4")

    class _MissingTypeResponse:
        def __init__(self):
            self.headers = {"Content-Length": "10"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    monkeypatch.setattr(
        s3_module, "urlopen", lambda request, timeout: _MissingTypeResponse()
    )
    with pytest.raises(StorageMediaError):
        provider.get_object_metadata("candidate-sessions/9/tasks/9/recordings/demo.mp4")

    def _raise_500(request, timeout):
        del request, timeout
        raise HTTPError(
            url="https://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(s3_module, "urlopen", _raise_500)
    with pytest.raises(StorageMediaError):
        provider.get_object_metadata("candidate-sessions/9/tasks/9/recordings/demo.mp4")


def test_s3_provider_get_object_metadata_negative_length_and_oserror(monkeypatch):
    provider = _build_s3_provider()

    class _NegativeLengthResponse:
        def __init__(self):
            self.headers = {"Content-Length": "-1", "Content-Type": "video/mp4"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    monkeypatch.setattr(
        s3_module, "urlopen", lambda request, timeout: _NegativeLengthResponse()
    )
    with pytest.raises(StorageMediaError):
        provider.get_object_metadata("candidate-sessions/9/tasks/9/recordings/demo.mp4")

    def _raise_oserror(request, timeout):
        del request, timeout
        raise OSError("socket closed")

    monkeypatch.setattr(s3_module, "urlopen", _raise_oserror)
    with pytest.raises(StorageMediaError):
        provider.get_object_metadata("candidate-sessions/9/tasks/9/recordings/demo.mp4")


def test_s3_provider_includes_session_token_when_configured():
    provider = S3StorageMediaProvider(
        endpoint="https://storage.example.com/base",
        region="us-east-1",
        bucket="media-bucket",
        access_key_id="AKIA_TEST",
        secret_access_key="secret_test_key",
        session_token="session-token-value",
    )
    download_url = provider.create_signed_download_url(
        "candidate-sessions/1/tasks/1/recordings/object.mp4",
        120,
    )
    assert "X-Amz-Security-Token=session-token-value" in download_url


def test_s3_provider_virtual_host_without_port():
    provider = S3StorageMediaProvider(
        endpoint="https://storage.example.com/base",
        region="us-east-1",
        bucket="media-bucket",
        access_key_id="AKIA_TEST",
        secret_access_key="secret_test_key",
        use_path_style=False,
    )
    download_url = provider.create_signed_download_url(
        "candidate-sessions/2/tasks/6/recordings/demo.webm",
        120,
    )
    assert download_url.startswith("https://media-bucket.storage.example.com/")
    assert "/base/candidate-sessions/2/tasks/6/recordings/demo.webm" in download_url


def test_s3_provider_init_validates_required_configuration():
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="",
            region="us-east-1",
            bucket="bucket",
            access_key_id="ak",
            secret_access_key="secret",
        )
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="https://s3.example",
            region="",
            bucket="bucket",
            access_key_id="ak",
            secret_access_key="secret",
        )
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="https://s3.example",
            region="us-east-1",
            bucket="",
            access_key_id="ak",
            secret_access_key="secret",
        )
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="https://s3.example",
            region="us-east-1",
            bucket="bucket",
            access_key_id="",
            secret_access_key="",
        )
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="not-a-url",
            region="us-east-1",
            bucket="bucket",
            access_key_id="ak",
            secret_access_key="secret",
        )
