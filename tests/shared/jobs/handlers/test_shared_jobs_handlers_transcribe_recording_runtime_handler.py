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


def test_is_retryable_transcription_error_rejects_blank_messages():
    assert (
        runtime_handler.is_retryable_transcription_error(RuntimeError("   ")) is False
    )


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

    async def _mark_retrying(*_args, **_kwargs):
        raise AssertionError("retryable path should not run for unavailable recording")

    result = await runtime_handler.handle_transcribe_recording_impl(
        {"recordingId": 42},
        parse_positive_int=lambda value: int(value) if value is not None else None,
        normalize_segments=lambda segments: segments,
        sanitize_error=lambda exc: str(exc),
        mark_processing=_mark_processing,
        mark_ready=_mark_ready,
        mark_failure=_mark_failure,
        mark_retrying=_mark_retrying,
        async_session_maker=lambda: _SessionContext(object()),
        recordings_repo=_RecordingsRepo(),
        get_storage_media_provider=lambda: object(),
        resolve_signed_url_ttl=lambda default: default,
        get_transcription_provider=lambda: object(),
        load_transcription_job=lambda **_kwargs: None,
        transcription_job_has_retry_headroom=lambda _job: False,
        is_retryable_transcription_error=runtime_handler.is_retryable_transcription_error,
        transcription_provider_error=RuntimeError,
        logger=_NoopLogger(),
    )

    assert result == {"status": "recording_unavailable", "recordingId": 42}


@pytest.mark.asyncio
async def test_handle_transcribe_recording_impl_uses_segments_when_text_is_blank():
    recording = SimpleNamespace(storage_key="recordings/key", content_type="video/mp4")
    ready_marked: list[tuple[int, str, list[dict[str, object]], str | None]] = []

    class _RecordingsRepo:
        async def get_by_id(self, _db, _recording_id):
            return recording

        def is_deleted_or_purged(self, _recording):
            return False

    class _StorageProvider:
        @staticmethod
        def create_signed_download_url(_storage_key, expires_seconds):
            assert expires_seconds == 300
            return "https://fake.example/download?key=recordings/key"

    class _Provider:
        @staticmethod
        def transcribe_recording(*, source_url: str, content_type: str):
            del source_url, content_type
            return SimpleNamespace(
                text="   ",
                segments=[
                    {"startMs": 0, "endMs": 1000, "text": "hello"},
                    {"startMs": 1000, "endMs": 2000, "text": "world"},
                ],
                model_name="mock-model",
            )

    async def _mark_processing(_recording_id):
        return "uploaded", "processing"

    async def _mark_ready(recording_id, *, text, segments, model_name):
        ready_marked.append((recording_id, text, segments, model_name))

    async def _mark_failure(*_args, **_kwargs):
        raise AssertionError("failure path should not run for segment-backed result")

    async def _mark_retrying(*_args, **_kwargs):
        raise AssertionError("retrying path should not run for segment-backed result")

    result = await runtime_handler.handle_transcribe_recording_impl(
        {"recordingId": 42, "companyId": 7},
        parse_positive_int=lambda value: int(value) if value is not None else None,
        normalize_segments=lambda segments: segments,
        sanitize_error=lambda exc: str(exc),
        mark_processing=_mark_processing,
        mark_ready=_mark_ready,
        mark_failure=_mark_failure,
        mark_retrying=_mark_retrying,
        async_session_maker=lambda: _SessionContext(object()),
        recordings_repo=_RecordingsRepo(),
        get_storage_media_provider=lambda: _StorageProvider(),
        resolve_signed_url_ttl=lambda default: default,
        get_transcription_provider=lambda: _Provider(),
        load_transcription_job=lambda **_kwargs: None,
        transcription_job_has_retry_headroom=lambda _job: False,
        is_retryable_transcription_error=runtime_handler.is_retryable_transcription_error,
        transcription_provider_error=RuntimeError,
        logger=_NoopLogger(),
    )

    assert result["status"] == "ready"
    assert result["recordingId"] == 42
    assert ready_marked == [
        (
            42,
            "hello world",
            [
                {"startMs": 0, "endMs": 1000, "text": "hello"},
                {"startMs": 1000, "endMs": 2000, "text": "world"},
            ],
            "mock-model",
        )
    ]


def test_is_retryable_transcription_error_detects_provider_throttling():
    error = RuntimeError("openai_transcription_failed:RateLimitError")

    assert runtime_handler.is_retryable_transcription_error(error) is True


@pytest.mark.asyncio
async def test_handle_transcribe_recording_impl_keeps_retryable_failures_nonterminal():
    recording = SimpleNamespace(storage_key="recordings/key", content_type="video/mp4")
    retry_marked: list[str] = []

    class _RecordingsRepo:
        async def get_by_id(self, _db, _recording_id):
            return recording

        def is_deleted_or_purged(self, _recording):
            return False

    class _StorageProvider:
        @staticmethod
        def create_signed_download_url(_storage_key, expires_seconds):
            assert expires_seconds == 300
            return "https://fake.example/download?key=recordings/key"

    class _BrokenProvider:
        @staticmethod
        def transcribe_recording(*, source_url: str, content_type: str):
            del source_url, content_type
            raise RuntimeError("openai_transcription_failed:RateLimitError")

    async def _mark_processing(_recording_id):
        return "uploaded", "processing"

    async def _mark_ready(*_args, **_kwargs):
        raise AssertionError("ready path should not run for retryable provider failure")

    async def _mark_failure(*_args, **_kwargs):
        raise AssertionError(
            "terminal failure should not run while retry headroom remains"
        )

    async def _mark_retrying(_recording_id, *, reason: str):
        retry_marked.append(reason)

    async def _load_transcription_job(*, company_id: int, recording_id: int):
        assert company_id == 7
        assert recording_id == 42
        return SimpleNamespace(attempt=1, max_attempts=7)

    with pytest.raises(
        RuntimeError,
        match="transcription_failed: openai_transcription_failed:RateLimitError",
    ):
        await runtime_handler.handle_transcribe_recording_impl(
            {"recordingId": 42, "companyId": 7},
            parse_positive_int=lambda value: int(value),
            normalize_segments=lambda segments: segments,
            sanitize_error=lambda exc: str(exc),
            mark_processing=_mark_processing,
            mark_ready=_mark_ready,
            mark_failure=_mark_failure,
            mark_retrying=_mark_retrying,
            async_session_maker=lambda: _SessionContext(object()),
            recordings_repo=_RecordingsRepo(),
            get_storage_media_provider=lambda: _StorageProvider(),
            resolve_signed_url_ttl=lambda default: default,
            get_transcription_provider=lambda: _BrokenProvider(),
            load_transcription_job=_load_transcription_job,
            transcription_job_has_retry_headroom=lambda job: job.attempt
            < job.max_attempts,
            is_retryable_transcription_error=runtime_handler.is_retryable_transcription_error,
            transcription_provider_error=RuntimeError,
            logger=_NoopLogger(),
        )

    assert retry_marked == ["openai_transcription_failed:RateLimitError"]


@pytest.mark.asyncio
async def test_handle_transcribe_recording_impl_falls_back_to_terminal_failure_when_job_lookup_errors():
    recording = SimpleNamespace(storage_key="recordings/key", content_type="video/mp4")
    failure_marked: list[str] = []

    class _RecordingsRepo:
        async def get_by_id(self, _db, _recording_id):
            return recording

        def is_deleted_or_purged(self, _recording):
            return False

    class _StorageProvider:
        @staticmethod
        def create_signed_download_url(_storage_key, expires_seconds):
            assert expires_seconds == 300
            return "https://fake.example/download?key=recordings/key"

    class _BrokenProvider:
        @staticmethod
        def transcribe_recording(*, source_url: str, content_type: str):
            del source_url, content_type
            raise RuntimeError("openai_transcription_failed:RateLimitError")

    async def _mark_processing(_recording_id):
        return "uploaded", "processing"

    async def _mark_ready(*_args, **_kwargs):
        raise AssertionError("ready path should not run for retryable provider failure")

    async def _mark_failure(_recording_id, *, reason: str):
        failure_marked.append(reason)

    async def _mark_retrying(*_args, **_kwargs):
        raise AssertionError("retrying path should not run when job lookup fails")

    async def _load_transcription_job(*, company_id: int, recording_id: int):
        assert company_id == 7
        assert recording_id == 42
        raise RuntimeError("job lookup unavailable")

    with pytest.raises(
        RuntimeError,
        match="transcription_failed: openai_transcription_failed:RateLimitError",
    ):
        await runtime_handler.handle_transcribe_recording_impl(
            {"recordingId": 42, "companyId": 7},
            parse_positive_int=lambda value: int(value),
            normalize_segments=lambda segments: segments,
            sanitize_error=lambda exc: str(exc),
            mark_processing=_mark_processing,
            mark_ready=_mark_ready,
            mark_failure=_mark_failure,
            mark_retrying=_mark_retrying,
            async_session_maker=lambda: _SessionContext(object()),
            recordings_repo=_RecordingsRepo(),
            get_storage_media_provider=lambda: _StorageProvider(),
            resolve_signed_url_ttl=lambda default: default,
            get_transcription_provider=lambda: _BrokenProvider(),
            load_transcription_job=_load_transcription_job,
            transcription_job_has_retry_headroom=lambda job: False,
            is_retryable_transcription_error=runtime_handler.is_retryable_transcription_error,
            transcription_provider_error=RuntimeError,
            logger=_NoopLogger(),
        )

    assert failure_marked == ["openai_transcription_failed:RateLimitError"]


@pytest.mark.asyncio
async def test_handle_transcribe_recording_impl_counts_running_job_as_in_flight_for_retry_headroom():
    recording = SimpleNamespace(storage_key="recordings/key", content_type="video/mp4")
    retry_marked: list[str] = []

    class _RecordingsRepo:
        async def get_by_id(self, _db, _recording_id):
            return recording

        def is_deleted_or_purged(self, _recording):
            return False

    class _StorageProvider:
        @staticmethod
        def create_signed_download_url(_storage_key, expires_seconds):
            assert expires_seconds == 300
            return "https://fake.example/download?key=recordings/key"

    class _BrokenProvider:
        @staticmethod
        def transcribe_recording(*, source_url: str, content_type: str):
            del source_url, content_type
            raise RuntimeError("openai_transcription_failed:RateLimitError")

    async def _mark_processing(_recording_id):
        return "uploaded", "processing"

    async def _mark_ready(*_args, **_kwargs):
        raise AssertionError("ready path should not run for retryable provider failure")

    async def _mark_failure(*_args, **_kwargs):
        raise AssertionError(
            "terminal failure should not run while retry headroom remains"
        )

    async def _mark_retrying(_recording_id, *, reason: str):
        retry_marked.append(reason)

    async def _load_transcription_job(*, company_id: int, recording_id: int):
        assert company_id == 7
        assert recording_id == 42
        return SimpleNamespace(status="running", attempt=0, max_attempts=2)

    with pytest.raises(
        RuntimeError,
        match="transcription_failed: openai_transcription_failed:RateLimitError",
    ):
        await runtime_handler.handle_transcribe_recording_impl(
            {"recordingId": 42, "companyId": 7},
            parse_positive_int=lambda value: int(value),
            normalize_segments=lambda segments: segments,
            sanitize_error=lambda exc: str(exc),
            mark_processing=_mark_processing,
            mark_ready=_mark_ready,
            mark_failure=_mark_failure,
            mark_retrying=_mark_retrying,
            async_session_maker=lambda: _SessionContext(object()),
            recordings_repo=_RecordingsRepo(),
            get_storage_media_provider=lambda: _StorageProvider(),
            resolve_signed_url_ttl=lambda default: default,
            get_transcription_provider=lambda: _BrokenProvider(),
            load_transcription_job=_load_transcription_job,
            transcription_job_has_retry_headroom=lambda job: job.attempt
            < job.max_attempts,
            is_retryable_transcription_error=runtime_handler.is_retryable_transcription_error,
            transcription_provider_error=RuntimeError,
            logger=_NoopLogger(),
        )

    assert retry_marked == ["openai_transcription_failed:RateLimitError"]
