from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_init_handoff_upload_success(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-success@test.com",
    )
    provider = FakeStorageMediaProvider()

    recording, upload_url, expires_seconds = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1024,
        filename="demo.mp4",
        storage_provider=provider,
    )

    assert recording.id > 0
    assert recording.status == "uploading"
    assert upload_url.startswith("https://fake-storage.local/upload?")
    assert expires_seconds > 0
