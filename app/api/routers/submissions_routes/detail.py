import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.current_user import get_current_user
from app.core.auth.roles import ensure_recruiter
from app.core.db import get_session
from app.core.errors import MEDIA_STORAGE_UNAVAILABLE, ApiError
from app.domains import User
from app.domains.candidate_sessions import repository as cs_repo
from app.domains.submissions import service_recruiter as recruiter_sub_service
from app.domains.submissions.presenter import present_detail
from app.domains.submissions.schemas import RecruiterSubmissionDetailOut
from app.integrations.storage_media import (
    get_storage_media_provider,
    resolve_signed_url_ttl,
)
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.recordings import repository as recordings_repo
from app.repositories.transcripts import repository as transcripts_repo

router = APIRouter(prefix="/submissions", tags=["submissions"])
logger = logging.getLogger(__name__)


@router.get("/{submission_id}", response_model=RecruiterSubmissionDetailOut)
async def get_submission_detail_route(
    submission_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> RecruiterSubmissionDetailOut:
    """Return recruiter-facing detail for a submission."""
    ensure_recruiter(user)
    sub, task, cs, sim = await recruiter_sub_service.fetch_detail(
        db,
        submission_id,
        user.id,
        recruiter_company_id=getattr(user, "company_id", None),
    )
    day_audit = None
    candidate_session_id = getattr(sub, "candidate_session_id", None)
    day_index = getattr(task, "day_index", None)
    if isinstance(candidate_session_id, int) and isinstance(day_index, int):
        day_audit = await cs_repo.get_day_audit(
            db,
            candidate_session_id=candidate_session_id,
            day_index=day_index,
        )

    recording = None
    transcript = None
    resolved_candidate_session_id = getattr(cs, "id", None) or getattr(
        sub, "candidate_session_id", None
    )
    resolved_task_id = getattr(task, "id", None) or getattr(sub, "task_id", None)
    submission_recording_id = getattr(sub, "recording_id", None)
    if isinstance(submission_recording_id, int):
        recording = await recordings_repo.get_by_id(db, submission_recording_id)

    if (
        recording is None
        and isinstance(resolved_candidate_session_id, int)
        and isinstance(resolved_task_id, int)
    ):
        recording = await recordings_repo.get_latest_for_task_session(
            db,
            candidate_session_id=resolved_candidate_session_id,
            task_id=resolved_task_id,
        )

    if recording is not None and (
        recording.candidate_session_id != resolved_candidate_session_id
        or recording.task_id != resolved_task_id
    ):
        recording = None

    if recording is not None and not recordings_repo.is_deleted_or_purged(recording):
        transcript = await transcripts_repo.get_by_recording_id(db, recording.id)

    recording_download_url = None
    if recordings_repo.is_downloadable(recording):
        expires_seconds = resolve_signed_url_ttl()
        try:
            storage_provider = get_storage_media_provider()
            recording_download_url = storage_provider.create_signed_download_url(
                recording.storage_key,
                expires_seconds=expires_seconds,
            )
        except (StorageMediaError, ValueError) as exc:
            raise ApiError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Media storage unavailable",
                error_code=MEDIA_STORAGE_UNAVAILABLE,
                retryable=True,
            ) from exc
        logger.info(
            "Recording download URL generated recordingId=%s submissionId=%s recruiterId=%s expiresInSeconds=%s",
            recording.id,
            sub.id,
            user.id,
            expires_seconds,
        )

    payload = present_detail(
        sub,
        task,
        cs,
        sim,
        day_audit=day_audit,
        recording=recording,
        transcript=transcript,
        recording_download_url=recording_download_url,
    )
    return RecruiterSubmissionDetailOut(**payload)
