from __future__ import annotations

from types import SimpleNamespace

from app.shared.http import shared_http_middleware_http_setup_middleware as middleware


def test_media_allowed_origins_include_fake_and_s3_endpoints(monkeypatch):
    monkeypatch.setattr(
        middleware.settings,
        "storage_media",
        SimpleNamespace(
            MEDIA_FAKE_BASE_URL="http://localhost:8000/api/recordings/storage/fake",
            MEDIA_S3_ENDPOINT="https://media.example.com/base",
        ),
    )

    assert middleware._media_allowed_origins() == {
        "http://localhost:8000",
        "https://media.example.com",
    }
