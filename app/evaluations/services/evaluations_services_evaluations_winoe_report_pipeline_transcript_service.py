"""Application module for evaluations services evaluations winoe report pipeline transcript service workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.recordings import repository as recordings_repo
from app.shared.database.shared_database_models_model import (
    RecordingAsset,
    Submission,
    Task,
    Transcript,
)


async def _resolve_day4_transcript(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    day4_task: Task | None,
    day4_submission: Submission | None,
) -> tuple[Transcript | None, str]:
    recording: RecordingAsset | None = None
    if day4_submission is not None and isinstance(day4_submission.recording_id, int):
        recording = await db.get(RecordingAsset, day4_submission.recording_id)
        if recordings_repo.is_deleted_or_purged(recording):
            recording = None

    if recording is None and day4_task is not None:
        recording = (
            await db.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session_id,
                    RecordingAsset.task_id == day4_task.id,
                )
                .order_by(RecordingAsset.created_at.desc(), RecordingAsset.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if recordings_repo.is_deleted_or_purged(recording):
            recording = None

    if recording is None:
        return None, "transcript:missing"

    transcript = (
        await db.execute(
            select(Transcript).where(
                Transcript.recording_id == recording.id,
                Transcript.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if transcript is None:
        return None, f"transcript:recording:{recording.id}:missing"
    return transcript, f"transcript:{transcript.id}"


__all__ = ["_resolve_day4_transcript", "recordings_repo"]
