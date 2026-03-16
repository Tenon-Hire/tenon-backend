from __future__ import annotations

import pytest

from app.integrations.transcription.base import TranscriptionResult
from app.jobs.handlers import transcribe_recording as handler
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_READY,
    RECORDING_ASSET_STATUS_UPLOADED,
)
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import (
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_PENDING,
    TRANSCRIPT_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_READY,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def test_parse_positive_int_variants():
    assert handler._parse_positive_int(True) is None
    assert handler._parse_positive_int(False) is None
    assert handler._parse_positive_int(0) is None
    assert handler._parse_positive_int(-1) is None
    assert handler._parse_positive_int(7) == 7
    assert handler._parse_positive_int("5") == 5
    assert handler._parse_positive_int("0") is None
    assert handler._parse_positive_int("x5") is None


def test_normalize_segments_filters_and_coerces_values():
    assert handler._normalize_segments(None) == []

    segments = handler._normalize_segments(
        [
            "skip-me",
            {"startMs": True, "endMs": 4.7, "text": " first "},
            {"startMs": " 12 ", "endMs": "oops", "text": "second"},
            {"startMs": 1, "endMs": 2},
        ]
    )
    assert segments == [
        {"startMs": 0, "endMs": 4, "text": "first"},
        {"startMs": 12, "endMs": 0, "text": "second"},
    ]


@pytest.mark.asyncio
async def test_transcribe_recording_handler_success(async_session):
    recruiter = await create_recruiter(async_session, email="transcribe-ok@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

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


@pytest.mark.asyncio
async def test_transcribe_recording_handler_invalid_payload_skips():
    result = await handler.handle_transcribe_recording({"recordingId": True})
    assert result["status"] == "skipped_invalid_payload"
    assert result["recordingId"] is True


@pytest.mark.asyncio
async def test_transcribe_recording_handler_missing_recording_returns_not_found():
    result = await handler.handle_transcribe_recording({"recordingId": 9_999_999})
    assert result["status"] == "recording_not_found"


@pytest.mark.asyncio
async def test_transcribe_recording_handler_deleted_recording_is_unavailable(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="transcribe-deleted@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/transcribe-deleted.mp4"
        ),
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_DELETED,
        commit=True,
    )
    recording.deleted_at = recording.created_at
    await async_session.commit()

    result = await handler.handle_transcribe_recording({"recordingId": recording.id})
    assert result["status"] == "recording_unavailable"


@pytest.mark.asyncio
async def test_transcribe_recording_handler_already_ready(async_session):
    recruiter = await create_recruiter(async_session, email="transcribe-ready@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/transcribe-ready.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_READY,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="already done",
        segments_json=[{"startMs": 0, "endMs": 1, "text": "already done"}],
        model_name="fake-stt-v1",
        commit=True,
    )

    result = await handler.handle_transcribe_recording({"recordingId": recording.id})
    assert result["status"] == "already_ready"


@pytest.mark.asyncio
async def test_transcribe_recording_handler_missing_after_processing(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="transcribe-missing@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)
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


@pytest.mark.asyncio
async def test_transcribe_recording_handler_failure_marks_failed(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(async_session, email="transcribe-fail@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/transcribe-fail.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )

    class _BrokenProvider:
        def transcribe_recording(self, *, source_url: str, content_type: str):
            del source_url, content_type
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        handler, "get_transcription_provider", lambda: _BrokenProvider()
    )
    recording_id = recording.id

    with pytest.raises(RuntimeError):
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
    assert "provider unavailable" in (refreshed_transcript.last_error or "")


@pytest.mark.asyncio
async def test_transcribe_recording_handler_empty_transcript_marks_failed(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(async_session, email="transcribe-empty@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

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


@pytest.mark.asyncio
async def test_transcribe_recording_handler_failure_from_processing_state(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="transcribe-processing-fail@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

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
