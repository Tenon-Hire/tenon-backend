from __future__ import annotations

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


def test_fake_provider_set_and_delete_object_metadata():
    provider = FakeStorageMediaProvider()
    key = "candidate-sessions/1/tasks/2/recordings/demo.mp4"
    provider.set_object_metadata(key, content_type="video/mp4", size_bytes=99)
    assert provider.get_object_metadata(key) is not None
    provider.delete_object(key)
    assert provider.get_object_metadata(key) is None
