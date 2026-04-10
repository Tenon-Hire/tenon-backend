from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_status_remains_available_after_window_closes_for_submitted_recording(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-status-post-cutoff@test.com"
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
            "filename": "cutoff-status.mp4",
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
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert complete_response.status_code == 200, complete_response.text

    _set_closed_windows(candidate_session)
    await async_session.commit()

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["recording"]["recordingId"] == recording_id
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADED
    assert body["recording"]["downloadUrl"] is not None
    assert "download?" in body["recording"]["downloadUrl"]
    assert body["transcript"]["status"] == TRANSCRIPT_STATUS_PENDING
    assert body["transcript"]["text"] is None
    assert body["transcript"]["segments"] is None
