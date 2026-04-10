from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_detail_includes_recording_and_transcript(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-detail@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session, trial=sim, status="in_progress"
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff summary",
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/seed.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4_096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="hello world transcript",
        segments_json=[{"startMs": 0, "endMs": 1000, "text": "hello"}],
        model_name="mock-stt-v1",
        commit=True,
    )
    submission.recording_id = recording.id
    await async_session.commit()

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["recordingId"] == f"rec_{recording.id}"
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADED
    assert body["recording"]["downloadUrl"] is not None
    assert "download?" in body["recording"]["downloadUrl"]
    assert body["transcript"]["status"] == TRANSCRIPT_STATUS_READY
    assert body["transcript"]["modelName"] == "mock-stt-v1"
    assert body["transcript"]["segments"] == [
        {"startMs": 0, "endMs": 1000, "text": "hello"}
    ]
    assert body["handoff"]["recordingId"] == f"rec_{recording.id}"
    assert body["handoff"]["downloadUrl"] is not None
    assert body["handoff"]["transcript"]["status"] == TRANSCRIPT_STATUS_READY
