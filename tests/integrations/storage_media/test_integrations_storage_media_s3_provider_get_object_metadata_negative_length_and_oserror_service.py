from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


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
