"""Application module for jobs handlers transcribe recording runtime handler workflows."""

from __future__ import annotations

import time
from types import SimpleNamespace

from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_PURGED,
    RECORDING_ASSET_STATUS_READY,
)
from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_READY,
)

_RETRYABLE_TRANSCRIPTION_ERROR_MARKERS = (
    "openai_transcription_failed:ratelimiterror",
    "openai_transcription_failed:apitimeouterror",
    "openai_transcription_failed:apiconnectionerror",
    "openai_transcription_failed:internalservererror",
    "openai_transcription_failed:serviceunavailableerror",
    "openai_transcription_failed:overloadederror",
    "rate limit",
    "too many requests",
    "429",
)


def _resolve_transcript_text(result) -> str:
    text = (getattr(result, "text", None) or "").strip()
    if text:
        return text
    segments = getattr(result, "segments", None)
    if not isinstance(segments, list):
        return ""
    parts: list[str] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_text = segment.get("text")
        if isinstance(segment_text, str) and segment_text.strip():
            parts.append(segment_text.strip())
    return " ".join(parts).strip()


def is_retryable_transcription_error(exc: Exception) -> bool:
    """Return whether a transcription error should remain non-terminal."""
    normalized = str(exc).strip().lower()
    if not normalized:
        return False
    return any(
        marker in normalized for marker in _RETRYABLE_TRANSCRIPTION_ERROR_MARKERS
    )


def _transcription_job_view_for_retry_headroom(job):
    if job is None:
        return None
    attempt = int(getattr(job, "attempt", 0) or 0)
    max_attempts = int(getattr(job, "max_attempts", 0) or 0)
    return SimpleNamespace(attempt=attempt + 1, max_attempts=max_attempts)


async def handle_transcribe_recording_impl(
    payload_json: dict,
    *,
    parse_positive_int,
    normalize_segments,
    sanitize_error,
    mark_processing,
    mark_ready,
    mark_failure,
    mark_retrying,
    async_session_maker,
    recordings_repo,
    get_storage_media_provider,
    resolve_signed_url_ttl,
    get_transcription_provider,
    load_transcription_job,
    transcription_job_has_retry_headroom,
    is_retryable_transcription_error,
    transcription_provider_error,
    logger,
):
    """Handle transcribe recording impl."""
    recording_id = parse_positive_int(payload_json.get("recordingId"))
    company_id = parse_positive_int(payload_json.get("companyId"))
    if recording_id is None:
        return {
            "status": "skipped_invalid_payload",
            "recordingId": payload_json.get("recordingId"),
        }
    started = time.perf_counter()
    logger.info("transcription_job_started recordingId=%s", recording_id)
    processing_state = await mark_processing(recording_id)
    if processing_state is None:
        return {"status": "recording_not_found", "recordingId": recording_id}
    recording_status, transcript_status = processing_state
    if recording_status in {
        RECORDING_ASSET_STATUS_DELETED,
        RECORDING_ASSET_STATUS_PURGED,
    }:
        return {"status": "recording_unavailable", "recordingId": recording_id}
    if (
        recording_status == RECORDING_ASSET_STATUS_READY
        and transcript_status == TRANSCRIPT_STATUS_READY
    ):
        return {"status": "already_ready", "recordingId": recording_id}
    try:
        async with async_session_maker() as db:
            recording = await recordings_repo.get_by_id(db, recording_id)
            if recording is None:
                return {"status": "recording_not_found", "recordingId": recording_id}
            if recordings_repo.is_deleted_or_purged(recording):
                return {"status": "recording_unavailable", "recordingId": recording_id}
            storage_key = recording.storage_key
            content_type = recording.content_type
        storage_provider = get_storage_media_provider()
        download_url = storage_provider.create_signed_download_url(
            storage_key, expires_seconds=resolve_signed_url_ttl(300)
        )
        transcription_provider = get_transcription_provider()
        result = transcription_provider.transcribe_recording(
            source_url=download_url, content_type=content_type
        )
        transcript_text = _resolve_transcript_text(result)
        if not transcript_text:
            raise transcription_provider_error(
                "provider returned empty transcript text"
            )
        await mark_ready(
            recording_id,
            text=transcript_text,
            segments=normalize_segments(result.segments),
            model_name=result.model_name,
        )
    except Exception as exc:
        error_reason = sanitize_error(exc)
        retrying_job = None
        if company_id is not None:
            try:
                retrying_job = await load_transcription_job(
                    company_id=company_id,
                    recording_id=recording_id,
                )
            except Exception:
                retrying_job = None
        duration_ms = int((time.perf_counter() - started) * 1000)
        retry_headroom_job = _transcription_job_view_for_retry_headroom(retrying_job)
        if is_retryable_transcription_error(
            exc
        ) and transcription_job_has_retry_headroom(retry_headroom_job):
            await mark_retrying(recording_id, reason=error_reason)
            logger.warning(
                "transcription_job_retryable_failure recordingId=%s attempt=%s maxAttempts=%s durationMs=%s reason=%s",
                recording_id,
                getattr(retrying_job, "attempt", None),
                getattr(retrying_job, "max_attempts", None),
                duration_ms,
                error_reason,
            )
            raise RuntimeError(f"transcription_failed: {error_reason}") from exc
        await mark_failure(recording_id, reason=error_reason)
        logger.warning(
            "transcription_job_failed recordingId=%s durationMs=%s reason=%s",
            recording_id,
            duration_ms,
            error_reason,
        )
        raise RuntimeError(f"transcription_failed: {error_reason}") from exc
    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "transcription_job_finished recordingId=%s durationMs=%s",
        recording_id,
        duration_ms,
    )
    return {"status": "ready", "recordingId": recording_id, "durationMs": duration_ms}


__all__ = [
    "handle_transcribe_recording_impl",
    "is_retryable_transcription_error",
]
