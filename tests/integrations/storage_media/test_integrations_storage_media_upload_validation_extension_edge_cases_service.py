from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


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
