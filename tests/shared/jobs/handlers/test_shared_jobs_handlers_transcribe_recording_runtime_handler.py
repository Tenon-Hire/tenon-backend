from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.jobs.handlers import (
    shared_jobs_handlers_transcribe_recording_runtime_handler as runtime_handler,
)


class _NoopLogger:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None


class _SessionContext:
    def __init__(self, db) -> None:
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


@pytest.mark.asyncio
async def test_handle_transcribe_recording_impl_returns_unavailable_when_repo_marks_deleted():
    recording = SimpleNamespace(storage_key="recordings/key", content_type="video/mp4")

    class _RecordingsRepo:
        async def get_by_id(self, _db, _recording_id):
            return recording

        def is_deleted_or_purged(self, _recording):
            return True

    async def _mark_processing(_recording_id):
        return "uploaded", "processing"

    async def _mark_ready(*_args, **_kwargs):
        raise AssertionError("ready path should not run when recording is unavailable")

    async def _mark_failure(*_args, **_kwargs):
        raise AssertionError("failure path should not run for unavailable recording")

    result = await runtime_handler.handle_transcribe_recording_impl(
        {"recordingId": 42},
        parse_positive_int=lambda value: int(value),
        normalize_segments=lambda segments: segments,
        sanitize_error=lambda exc: str(exc),
        mark_processing=_mark_processing,
        mark_ready=_mark_ready,
        mark_failure=_mark_failure,
        async_session_maker=lambda: _SessionContext(object()),
        recordings_repo=_RecordingsRepo(),
        get_storage_media_provider=lambda: object(),
        resolve_signed_url_ttl=lambda default: default,
        get_transcription_provider=lambda: object(),
        transcription_provider_error=RuntimeError,
        logger=_NoopLogger(),
    )

    assert result == {"status": "recording_unavailable", "recordingId": 42}
