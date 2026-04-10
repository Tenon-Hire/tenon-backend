from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *
from tests.media.routes.media_handoff_upload_resubmission_api_utils import *


@pytest.mark.asyncio
async def test_handoff_resubmission_replaces_submission_pointer_and_preserves_history(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-resubmit@test.com"
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

    first_init, first_recording = await _init_and_complete_upload(
        async_client,
        async_session,
        task_id=task.id,
        candidate_session_id=candidate_session.id,
        headers=headers,
        size_bytes=1_111,
        filename="first.mp4",
    )
    second_init, second_recording = await _init_and_complete_upload(
        async_client,
        async_session,
        task_id=task.id,
        candidate_session_id=candidate_session.id,
        headers=headers,
        size_bytes=2_222,
        filename="second.mp4",
    )
    assert second_recording.id != first_recording.id

    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == task.id,
            )
        )
    ).scalar_one()
    first_transcript = (
        await async_session.execute(
            select(Transcript).where(Transcript.recording_id == first_recording.id)
        )
    ).scalar_one()
    second_transcript = (
        await async_session.execute(
            select(Transcript).where(Transcript.recording_id == second_recording.id)
        )
    ).scalar_one()
    assert submission.recording_id == second_recording.id
    assert first_transcript.id != second_transcript.id

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    assert (
        status_response.json()["recording"]["recordingId"]
        == second_init.json()["recordingId"]
    )
