"""Application module for jobs handlers transcribe recording state handler workflows."""

from __future__ import annotations

from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_READY,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_PENDING,
    TRANSCRIPT_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_READY,
)


async def _mark_processing(recording_id: int, *, async_session_maker):
    async with async_session_maker() as db:
        recording = await recordings_repo.get_by_id_for_update(db, recording_id)
        if recording is None:
            return None
        if recordings_repo.is_deleted_or_purged(recording):
            return recording.status, TRANSCRIPT_STATUS_PENDING
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


async def _mark_failure(recording_id: int, *, reason: str, async_session_maker):
    async with async_session_maker() as db:
        recording = await recordings_repo.get_by_id_for_update(db, recording_id)
        if recording is None or recordings_repo.is_deleted_or_purged(recording):
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
    async_session_maker,
):
    async with async_session_maker() as db:
        recording = await recordings_repo.get_by_id_for_update(db, recording_id)
        if recording is None or recordings_repo.is_deleted_or_purged(recording):
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


__all__ = ["_mark_failure", "_mark_processing", "_mark_ready"]
