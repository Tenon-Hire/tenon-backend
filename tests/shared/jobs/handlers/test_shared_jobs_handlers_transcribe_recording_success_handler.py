from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_utils import *


@pytest.mark.asyncio
async def test_transcribe_recording_handler_success(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="transcribe-ok@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, trial=sim)

    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/transcribe-ok.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_PENDING,
        commit=True,
    )
    recording_id = recording.id

    result = await handler.handle_transcribe_recording({"recordingId": recording_id})
    assert result["status"] == "ready"

    async_session.expire_all()
    refreshed_recording = await recordings_repo.get_by_id(async_session, recording_id)
    refreshed_transcript = await transcripts_repo.get_by_recording_id(
        async_session, recording_id
    )
    assert refreshed_recording is not None
    assert refreshed_recording.status == RECORDING_ASSET_STATUS_READY
    assert refreshed_transcript is not None
    assert refreshed_transcript.status == TRANSCRIPT_STATUS_READY
    assert refreshed_transcript.text is not None
    assert refreshed_transcript.segments_json
    assert refreshed_transcript.model_name == "fake-stt-v1"
    assert refreshed_transcript.last_error is None
