from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_detail_uses_submission_recording_pointer_not_latest_attempt(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-pointer@test.com"
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
    first_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/first.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4_096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=first_recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="first transcript",
        segments_json=[{"startMs": 0, "endMs": 1000, "text": "first"}],
        model_name="mock-stt-v1",
        commit=True,
    )

    # Later recording exists but is not linked by submission.recording_id.
    latest_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/later.mp4"
        ),
        content_type="video/mp4",
        bytes_count=8_192,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=latest_recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="latest transcript",
        segments_json=[{"startMs": 0, "endMs": 1000, "text": "latest"}],
        model_name="mock-stt-v1",
        commit=True,
    )

    submission.recording_id = first_recording.id
    await async_session.commit()

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["recordingId"] == f"rec_{first_recording.id}"
    assert body["transcript"]["text"] == "first transcript"
