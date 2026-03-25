from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


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
