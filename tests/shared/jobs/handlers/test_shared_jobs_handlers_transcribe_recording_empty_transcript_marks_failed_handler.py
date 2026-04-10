from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_utils import *


@pytest.mark.asyncio
async def test_transcribe_recording_handler_empty_transcript_marks_failed(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="transcribe-empty@test.com"
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
            "recordings/transcribe-empty.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )

    class _EmptyProvider:
        def transcribe_recording(self, *, source_url: str, content_type: str):
            del source_url, content_type
            return TranscriptionResult(
                text="   ",
                segments=["bad-segment"],
                model_name="empty-model",
            )

    monkeypatch.setattr(handler, "get_transcription_provider", lambda: _EmptyProvider())
    recording_id = recording.id

    with pytest.raises(RuntimeError, match="provider returned empty transcript text"):
        await handler.handle_transcribe_recording({"recordingId": recording_id})

    async_session.expire_all()
    refreshed_recording = await recordings_repo.get_by_id(async_session, recording_id)
    refreshed_transcript = await transcripts_repo.get_by_recording_id(
        async_session, recording_id
    )
    assert refreshed_recording is not None
    assert refreshed_recording.status == RECORDING_ASSET_STATUS_FAILED
    assert refreshed_transcript is not None
    assert refreshed_transcript.status == TRANSCRIPT_STATUS_FAILED
    assert refreshed_transcript.last_error is not None
    assert "provider returned empty transcript text" in refreshed_transcript.last_error
