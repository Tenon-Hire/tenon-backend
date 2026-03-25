from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_get_handoff_status_falls_back_to_latest_recording_without_submission(
    async_session,
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-status-fallback@test.com",
    )
    provider = FakeStorageMediaProvider()
    latest, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=777,
        filename="latest.mp4",
        storage_provider=provider,
    )

    recording, transcript = await get_handoff_status(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
    )
    assert recording is not None
    assert recording.id == latest.id
    assert transcript is None
