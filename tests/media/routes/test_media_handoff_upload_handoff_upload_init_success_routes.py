from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_init_success(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-init@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(candidate_session),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "demo.mp4",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recordingId"].startswith("rec_")
    assert "upload?" in body["uploadUrl"]
    assert body["expiresInSeconds"] == 900

    recording = (
        await async_session.execute(
            select(RecordingAsset).where(RecordingAsset.task_id == task.id)
        )
    ).scalar_one()
    assert recording.status == RECORDING_ASSET_STATUS_UPLOADING
    assert recording.candidate_session_id == candidate_session.id
    assert recording.content_type == "video/mp4"
