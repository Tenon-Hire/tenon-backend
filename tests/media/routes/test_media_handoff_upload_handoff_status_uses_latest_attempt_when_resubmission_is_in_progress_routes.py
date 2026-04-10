from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_status_uses_latest_attempt_when_resubmission_is_in_progress(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-status-latest-attempt@test.com"
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

    first_init = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "first.mp4",
        },
    )
    assert first_init.status_code == 200, first_init.text
    first_recording = (
        (
            await async_session.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session.id,
                    RecordingAsset.task_id == task.id,
                )
                .order_by(RecordingAsset.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert first_recording is not None
    _fake_storage_provider().set_object_metadata(
        first_recording.storage_key,
        content_type=first_recording.content_type,
        size_bytes=first_recording.bytes,
    )
    first_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": first_init.json()["recordingId"]},
    )
    assert first_complete.status_code == 200, first_complete.text

    second_init = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_048,
            "filename": "second.mp4",
        },
    )
    assert second_init.status_code == 200, second_init.text
    assert second_init.json()["recordingId"] != first_init.json()["recordingId"]

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["recording"]["recordingId"] == second_init.json()["recordingId"]
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADING
    assert body["recording"]["downloadUrl"] is None
    assert body["transcript"] is None
