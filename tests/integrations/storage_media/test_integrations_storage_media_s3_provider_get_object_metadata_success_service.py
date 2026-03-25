from __future__ import annotations

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


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
