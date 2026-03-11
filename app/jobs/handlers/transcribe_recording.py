from __future__ import annotations

import logging
import time
from typing import Any

from app.core.db import async_session_maker
from app.integrations.storage_media import (
    get_storage_media_provider,
    resolve_signed_url_ttl,
)
from app.integrations.transcription import (
    TranscriptionProviderError,
    get_transcription_provider,
)
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_READY,
)
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import (
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_PENDING,
    TRANSCRIPT_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_READY,
)
from app.services.media.transcription_jobs import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
)

logger = logging.getLogger(__name__)


def _parse_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def _sanitize_error(exc: Exception) -> str:
    normalized = " ".join(str(exc).split())
    return normalized[:512]


def _coerce_non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    if isinstance(value, str) and value.strip().isdigit():
        return max(0, int(value.strip()))
    return 0


def _normalize_segments(raw_segments: Any) -> list[dict[str, object]]:
    if not isinstance(raw_segments, list):
        return []

    normalized: list[dict[str, object]] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        normalized.append(
            {
                "startMs": _coerce_non_negative_int(item.get("startMs")),
                "endMs": _coerce_non_negative_int(item.get("endMs")),
                "text": text.strip(),
            }
        )
    return normalized


async def _mark_processing(recording_id: int) -> tuple[str, str] | None:
    async with async_session_maker() as db:
        recording = await recordings_repo.get_by_id_for_update(db, recording_id)
        if recording is None:
            return None

        transcript, _ = await transcripts_repo.get_or_create_transcript(
            db,
            recording_id=recording.id,
            status=TRANSCRIPT_STATUS_PENDING,
            commit=False,
        )
        if (
            recording.status == RECORDING_ASSET_STATUS_READY
            and transcript.status == TRANSCRIPT_STATUS_READY
        ):
            return recording.status, transcript.status

        recording.status = RECORDING_ASSET_STATUS_PROCESSING
        await transcripts_repo.update_transcript(
            db,
            transcript=transcript,
            status=TRANSCRIPT_STATUS_PROCESSING,
            last_error=None,
            commit=False,
        )
        await db.commit()
        return recording.status, transcript.status


async def _mark_failure(recording_id: int, *, reason: str) -> None:
    async with async_session_maker() as db:
        recording = await recordings_repo.get_by_id_for_update(db, recording_id)
        if recording is None:
            return

        transcript, _ = await transcripts_repo.get_or_create_transcript(
            db,
            recording_id=recording.id,
            status=TRANSCRIPT_STATUS_PENDING,
            commit=False,
        )
        recording.status = RECORDING_ASSET_STATUS_FAILED
        await transcripts_repo.update_transcript(
            db,
            transcript=transcript,
            status=TRANSCRIPT_STATUS_FAILED,
            text=None,
            segments_json=None,
            model_name=None,
            last_error=reason,
            commit=False,
        )
        await db.commit()


async def _mark_ready(
    recording_id: int,
    *,
    text: str,
    segments: list[dict[str, object]],
    model_name: str | None,
) -> None:
    async with async_session_maker() as db:
        recording = await recordings_repo.get_by_id_for_update(db, recording_id)
        if recording is None:
            return

        transcript, _ = await transcripts_repo.get_or_create_transcript(
            db,
            recording_id=recording.id,
            status=TRANSCRIPT_STATUS_PENDING,
            commit=False,
        )
        recording.status = RECORDING_ASSET_STATUS_READY
        await transcripts_repo.update_transcript(
            db,
            transcript=transcript,
            status=TRANSCRIPT_STATUS_READY,
            text=text,
            segments_json=segments,
            model_name=model_name,
            last_error=None,
            commit=False,
        )
        await db.commit()


async def handle_transcribe_recording(payload_json: dict[str, Any]) -> dict[str, Any]:
    recording_id = _parse_positive_int(payload_json.get("recordingId"))
    if recording_id is None:
        return {
            "status": "skipped_invalid_payload",
            "recordingId": payload_json.get("recordingId"),
        }

    started = time.perf_counter()
    logger.info(
        "transcription_job_started recordingId=%s",
        recording_id,
    )

    processing_state = await _mark_processing(recording_id)
    if processing_state is None:
        return {
            "status": "recording_not_found",
            "recordingId": recording_id,
        }

    recording_status, transcript_status = processing_state
    if (
        recording_status == RECORDING_ASSET_STATUS_READY
        and transcript_status == TRANSCRIPT_STATUS_READY
    ):
        return {
            "status": "already_ready",
            "recordingId": recording_id,
        }

    try:
        async with async_session_maker() as db:
            recording = await recordings_repo.get_by_id(db, recording_id)
            if recording is None:
                return {
                    "status": "recording_not_found",
                    "recordingId": recording_id,
                }
            storage_key = recording.storage_key
            content_type = recording.content_type

        storage_provider = get_storage_media_provider()
        download_url = storage_provider.create_signed_download_url(
            storage_key,
            expires_seconds=resolve_signed_url_ttl(300),
        )
        transcription_provider = get_transcription_provider()
        result = transcription_provider.transcribe_recording(
            source_url=download_url,
            content_type=content_type,
        )
        normalized_segments = _normalize_segments(result.segments)
        transcript_text = (result.text or "").strip()
        if not transcript_text:
            raise TranscriptionProviderError("provider returned empty transcript text")

        await _mark_ready(
            recording_id,
            text=transcript_text,
            segments=normalized_segments,
            model_name=result.model_name,
        )
    except Exception as exc:
        error_reason = _sanitize_error(exc)
        await _mark_failure(recording_id, reason=error_reason)
        duration_ms = int((time.perf_counter() - started) * 1000)
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
    return {
        "status": "ready",
        "recordingId": recording_id,
        "durationMs": duration_ms,
    }


__all__ = [
    "TRANSCRIBE_RECORDING_JOB_TYPE",
    "handle_transcribe_recording",
]
