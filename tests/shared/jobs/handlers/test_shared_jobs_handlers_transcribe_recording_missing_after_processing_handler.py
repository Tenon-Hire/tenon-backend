from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_utils import *


@pytest.mark.asyncio
async def test_transcribe_recording_handler_missing_after_processing(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="transcribe-missing@test.com"
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
            "recordings/transcribe-missing.mp4"
        ),
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_PENDING,
        commit=True,
    )

    async def _return_none(*args, **kwargs):
        del args, kwargs
        return None

    monkeypatch.setattr(recordings_repo, "get_by_id", _return_none)
    result = await handler.handle_transcribe_recording({"recordingId": recording.id})
    assert result["status"] == "recording_not_found"
