from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_complete_rejects_overlong_duration(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-duration@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_048,
            "filename": "too-long.mp4",
            "durationSeconds": 901,
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_id = init_response.json()["recordingId"]
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
        duration_seconds=901,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert complete_response.status_code == 422, complete_response.text
    assert "15 minute limit" in complete_response.json()["detail"]
