from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_status_is_candidate_scoped_and_does_not_leak_other_candidate_data(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-status-scope@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session_a = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="status-a@test.com",
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    candidate_session_b = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="status-b@test.com",
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    headers_a = candidate_header_factory(candidate_session_a)
    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers_a,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "scope.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session_a.id,
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
        headers=headers_a,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 200, complete_response.text

    other_status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=candidate_header_factory(candidate_session_b),
    )
    assert other_status_response.status_code == 200, other_status_response.text
    body = other_status_response.json()
    assert body["recording"] is None
    assert body["transcript"] is None
