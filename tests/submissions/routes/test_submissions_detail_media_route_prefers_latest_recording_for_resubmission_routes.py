from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.submissions.routes.submissions_detail_media_routes_utils import *


@pytest.mark.asyncio
async def test_submission_detail_route_prefers_latest_recording_for_resubmission(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session,
        email="detail-route-latest@test.com",
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
    first_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/first.mp4"
        ),
        content_type="video/mp4",
        bytes_count=2048,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        created_at=datetime.now(UTC),
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=first_recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="first transcript",
        model_name="test-model",
        commit=True,
    )

    second_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/second.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        created_at=datetime.now(UTC) + timedelta(seconds=1),
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=second_recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="second transcript",
        model_name="test-model",
        commit=True,
    )
    submission.recording_id = first_recording.id
    await async_session.commit()

    payload = await detail_route.get_submission_detail_route(
        submission_id=submission.id,
        db=async_session,
        user=talent_partner,
    )

    assert payload.recording is not None
    assert payload.recording.recordingId == f"rec_{second_recording.id}"
    assert payload.handoff is not None
    assert payload.handoff.recordingId == f"rec_{second_recording.id}"
    assert payload.handoff.transcript is not None
    assert payload.handoff.transcript.text == "second transcript"
