from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


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
