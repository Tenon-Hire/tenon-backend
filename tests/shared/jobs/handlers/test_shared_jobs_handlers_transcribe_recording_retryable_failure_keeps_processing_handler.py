from __future__ import annotations

import pytest

from app.media.services.media_services_media_transcription_jobs_service import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    TRANSCRIBE_RECORDING_MAX_ATTEMPTS,
    build_transcribe_recording_payload,
    transcribe_recording_idempotency_key,
)
from app.shared.jobs.repositories import repository as jobs_repo
from tests.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_utils import *


@pytest.mark.asyncio
async def test_transcribe_recording_handler_retryable_failure_keeps_processing(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="transcribe-retryable@test.com"
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
            "recordings/transcribe-retryable.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    recording_id = recording.id

    await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=TRANSCRIBE_RECORDING_JOB_TYPE,
        idempotency_key=transcribe_recording_idempotency_key(recording_id),
        payload_json=build_transcribe_recording_payload(
            recording_id=recording_id,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            company_id=sim.company_id,
        ),
        company_id=sim.company_id,
        candidate_session_id=candidate_session.id,
        max_attempts=TRANSCRIBE_RECORDING_MAX_ATTEMPTS,
        correlation_id=f"recording:{recording_id}",
        commit=True,
    )

    class _RetryableProvider:
        def transcribe_recording(self, *, source_url: str, content_type: str):
            del source_url, content_type
            raise RuntimeError("openai_transcription_failed:RateLimitError")

    monkeypatch.setattr(
        handler, "get_transcription_provider", lambda: _RetryableProvider()
    )

    with pytest.raises(RuntimeError, match="transcription_failed"):
        await handler.handle_transcribe_recording(
            {"recordingId": recording_id, "companyId": sim.company_id}
        )

    async_session.expire_all()
    refreshed_recording = await recordings_repo.get_by_id(async_session, recording_id)
    refreshed_transcript = await transcripts_repo.get_by_recording_id(
        async_session, recording_id
    )
    assert refreshed_recording is not None
    assert refreshed_recording.status == RECORDING_ASSET_STATUS_PROCESSING
    assert refreshed_transcript is not None
    assert refreshed_transcript.status == TRANSCRIPT_STATUS_PROCESSING
    assert "RateLimitError" in (refreshed_transcript.last_error or "")
