from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_get_handoff_status_returns_latest_attempt_over_submission_pointer(
    async_session,
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-status-pointer@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    first_recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1024,
        filename="first.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        first_recording.storage_key,
        content_type=first_recording.content_type,
        size_bytes=first_recording.bytes,
    )
    await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{first_recording.id}",
        storage_provider=provider,
    )

    # New init creates a newer recording attempt; candidate status should
    # reflect this latest in-progress attempt immediately.
    latest_recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1536,
        filename="second.mp4",
        storage_provider=provider,
    )

    recording, transcript = await get_handoff_status(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
    )
    assert recording is not None
    assert recording.id == latest_recording.id
    assert recording.status == "uploading"
    assert transcript is None
