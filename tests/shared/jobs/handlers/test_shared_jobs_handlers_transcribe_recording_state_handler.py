from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_READY,
)
from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_PENDING,
    TRANSCRIPT_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_READY,
)
from app.shared.jobs.handlers import (
    shared_jobs_handlers_transcribe_recording_state_handler as state_handler,
)


class _FakeDB:
    def __init__(self):
        self.commit_calls = 0

    async def commit(self):
        self.commit_calls += 1


class _FakeSessionContext:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSessionMaker:
    def __init__(self, db):
        self._db = db

    def __call__(self):
        return _FakeSessionContext(self._db)


@pytest.mark.asyncio
async def test_mark_processing_early_returns_when_recording_and_transcript_already_ready(
    monkeypatch,
):
    db = _FakeDB()
    recording = SimpleNamespace(id=123, status=RECORDING_ASSET_STATUS_READY)
    transcript = SimpleNamespace(status=TRANSCRIPT_STATUS_READY)

    async def _get_recording(_db, _recording_id):
        return recording

    async def _get_or_create_transcript(*_args, **_kwargs):
        return transcript, False

    async def _update_transcript(*_args, **_kwargs):
        raise AssertionError("update_transcript should not be called")

    monkeypatch.setattr(
        state_handler.recordings_repo, "get_by_id_for_update", _get_recording
    )
    monkeypatch.setattr(
        state_handler.recordings_repo, "is_deleted_or_purged", lambda _recording: False
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo,
        "get_or_create_transcript",
        _get_or_create_transcript,
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo, "update_transcript", _update_transcript
    )

    result = await state_handler._mark_processing(
        123, async_session_maker=_FakeSessionMaker(db)
    )

    assert result == (RECORDING_ASSET_STATUS_READY, TRANSCRIPT_STATUS_READY)
    assert db.commit_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("recording", "is_deleted"),
    [
        (None, False),
        (SimpleNamespace(id=50, status=RECORDING_ASSET_STATUS_PROCESSING), True),
    ],
)
async def test_mark_failure_is_noop_for_missing_or_deleted_recording(
    monkeypatch, recording, is_deleted: bool
):
    db = _FakeDB()

    async def _get_recording(_db, _recording_id):
        return recording

    async def _get_or_create_transcript(*_args, **_kwargs):
        raise AssertionError("transcript creation should not be called")

    async def _update_transcript(*_args, **_kwargs):
        raise AssertionError("transcript update should not be called")

    monkeypatch.setattr(
        state_handler.recordings_repo, "get_by_id_for_update", _get_recording
    )
    monkeypatch.setattr(
        state_handler.recordings_repo,
        "is_deleted_or_purged",
        lambda _recording: is_deleted,
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo,
        "get_or_create_transcript",
        _get_or_create_transcript,
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo, "update_transcript", _update_transcript
    )

    await state_handler._mark_failure(
        50, reason="provider down", async_session_maker=_FakeSessionMaker(db)
    )

    assert db.commit_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("recording", "is_deleted"),
    [
        (None, False),
        (SimpleNamespace(id=51, status=RECORDING_ASSET_STATUS_PROCESSING), True),
    ],
)
async def test_mark_ready_is_noop_for_missing_or_deleted_recording(
    monkeypatch, recording, is_deleted: bool
):
    db = _FakeDB()

    async def _get_recording(_db, _recording_id):
        return recording

    async def _get_or_create_transcript(*_args, **_kwargs):
        raise AssertionError("transcript creation should not be called")

    async def _update_transcript(*_args, **_kwargs):
        raise AssertionError("transcript update should not be called")

    monkeypatch.setattr(
        state_handler.recordings_repo, "get_by_id_for_update", _get_recording
    )
    monkeypatch.setattr(
        state_handler.recordings_repo,
        "is_deleted_or_purged",
        lambda _recording: is_deleted,
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo,
        "get_or_create_transcript",
        _get_or_create_transcript,
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo, "update_transcript", _update_transcript
    )

    await state_handler._mark_ready(
        51,
        text="done",
        segments=[{"startMs": 0, "endMs": 1, "text": "done"}],
        model_name="model-x",
        async_session_maker=_FakeSessionMaker(db),
    )

    assert db.commit_calls == 0


@pytest.mark.asyncio
async def test_mark_failure_updates_transcript_and_commits(monkeypatch):
    db = _FakeDB()
    recording = SimpleNamespace(id=66, status=RECORDING_ASSET_STATUS_PROCESSING)
    transcript = SimpleNamespace(status=TRANSCRIPT_STATUS_PENDING)
    captured_update: dict[str, object] = {}

    async def _get_recording(_db, _recording_id):
        return recording

    async def _get_or_create_transcript(*_args, **_kwargs):
        return transcript, False

    async def _update_transcript(_db, **kwargs):
        captured_update.update(kwargs)
        transcript.status = kwargs["status"]

    monkeypatch.setattr(
        state_handler.recordings_repo, "get_by_id_for_update", _get_recording
    )
    monkeypatch.setattr(
        state_handler.recordings_repo, "is_deleted_or_purged", lambda _recording: False
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo,
        "get_or_create_transcript",
        _get_or_create_transcript,
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo, "update_transcript", _update_transcript
    )

    await state_handler._mark_failure(
        66, reason="transcription failed", async_session_maker=_FakeSessionMaker(db)
    )

    assert recording.status == RECORDING_ASSET_STATUS_FAILED
    assert transcript.status == TRANSCRIPT_STATUS_FAILED
    assert captured_update["status"] == TRANSCRIPT_STATUS_FAILED
    assert captured_update["last_error"] == "transcription failed"
    assert captured_update["commit"] is False
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_mark_ready_updates_transcript_and_commits(monkeypatch):
    db = _FakeDB()
    recording = SimpleNamespace(id=77, status=RECORDING_ASSET_STATUS_PROCESSING)
    transcript = SimpleNamespace(status=TRANSCRIPT_STATUS_PENDING)
    captured_update: dict[str, object] = {}

    async def _get_recording(_db, _recording_id):
        return recording

    async def _get_or_create_transcript(*_args, **_kwargs):
        return transcript, False

    async def _update_transcript(_db, **kwargs):
        captured_update.update(kwargs)
        transcript.status = kwargs["status"]

    monkeypatch.setattr(
        state_handler.recordings_repo, "get_by_id_for_update", _get_recording
    )
    monkeypatch.setattr(
        state_handler.recordings_repo, "is_deleted_or_purged", lambda _recording: False
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo,
        "get_or_create_transcript",
        _get_or_create_transcript,
    )
    monkeypatch.setattr(
        state_handler.transcripts_repo, "update_transcript", _update_transcript
    )

    segments = [{"startMs": 0, "endMs": 10, "text": "hello"}]
    await state_handler._mark_ready(
        77,
        text="hello",
        segments=segments,
        model_name="stt-v2",
        async_session_maker=_FakeSessionMaker(db),
    )

    assert recording.status == RECORDING_ASSET_STATUS_READY
    assert transcript.status == TRANSCRIPT_STATUS_READY
    assert captured_update["status"] == TRANSCRIPT_STATUS_READY
    assert captured_update["text"] == "hello"
    assert captured_update["segments_json"] == segments
    assert captured_update["model_name"] == "stt-v2"
    assert captured_update["last_error"] is None
    assert captured_update["commit"] is False
    assert db.commit_calls == 1
