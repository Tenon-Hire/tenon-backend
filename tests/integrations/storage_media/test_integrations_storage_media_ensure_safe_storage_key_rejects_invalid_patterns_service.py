from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


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
