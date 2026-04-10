from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_detail_media_routes_utils import *


@pytest.mark.asyncio
async def test_submission_detail_route_includes_media_payload(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="detail-route-success@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff notes",
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/detail.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="hello transcript",
        model_name="test-model",
        commit=True,
    )
    submission.recording_id = recording.id
    await async_session.commit()

    payload = await detail_route.get_submission_detail_route(
        submission_id=submission.id,
        db=async_session,
        user=talent_partner,
    )

    assert payload.recording is not None
    assert payload.recording.recordingId == f"rec_{recording.id}"
    assert payload.recording.downloadUrl is not None
    assert payload.transcript is not None
    assert payload.transcript.status == TRANSCRIPT_STATUS_READY
    assert payload.handoff is not None
    assert payload.handoff.recordingId == f"rec_{recording.id}"
