"""Application module for media services media handoff upload status service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import repository as transcripts_repo
from app.media.services.media_services_media_handoff_upload_validation_service import (
    ensure_handoff_task,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    RecordingAsset,
    Transcript,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)


async def get_handoff_status(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
) -> tuple[RecordingAsset | None, Transcript | None]:
    """Return handoff status."""
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    ensure_handoff_task(task.type)
    recording = await recordings_repo.get_latest_for_task_session(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    transcript = (
        await transcripts_repo.get_by_recording_id(db, recording.id)
        if recording is not None
        else None
    )
    return recording, transcript


__all__ = ["get_handoff_status"]
