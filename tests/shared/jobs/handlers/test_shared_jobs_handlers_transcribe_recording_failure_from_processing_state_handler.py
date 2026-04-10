from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_utils import *


@pytest.mark.asyncio
async def test_transcribe_recording_handler_failure_from_processing_state(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="transcribe-processing-fail@test.com"
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
            "recordings/transcribe-processing.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_PROCESSING,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_PROCESSING,
        commit=True,
    )

    class _BrokenProvider:
        def transcribe_recording(self, *, source_url: str, content_type: str):
            del source_url, content_type
            raise RuntimeError("processing failure")

    monkeypatch.setattr(
        handler, "get_transcription_provider", lambda: _BrokenProvider()
    )
    recording_id = recording.id

    with pytest.raises(RuntimeError, match="processing failure"):
        await handler.handle_transcribe_recording({"recordingId": recording_id})

    async_session.expire_all()
    refreshed_transcript = await transcripts_repo.get_by_recording_id(
        async_session, recording_id
    )
    assert refreshed_transcript is not None
    assert refreshed_transcript.status == TRANSCRIPT_STATUS_FAILED
