from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    StorageMediaError,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import (
    TRANSCRIPT_STATUS_PENDING,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.media.services.media_services_media_handoff_upload_service import (
    _load_task_with_company_or_404,
    _resolve_company_id,
    _upsert_submission_recording_pointer,
    complete_handoff_upload,
    get_handoff_status,
    init_handoff_upload,
)
from app.media.services.media_services_media_transcription_jobs_service import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    transcribe_recording_idempotency_key,
)
from app.shared.database.shared_database_models_model import Job
from app.shared.utils.shared_utils_errors_utils import (
    MEDIA_STORAGE_UNAVAILABLE,
    REQUEST_TOO_LARGE,
)
from app.submissions.repositories import repository as submissions_repo
from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
    create_trial,
)

CONSENT_KWARGS = {"consent_version": "mvp1", "ai_notice_version": "mvp1"}


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def _non_handoff_task(tasks):
    return next(task for task in tasks if task.type != "handoff")


async def _setup_handoff_context(
    async_session,
    email: str,
    *,
    consented: bool = False,
):
    talent_partner = await create_talent_partner(async_session, email=email)
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
        **(CONSENT_KWARGS if consented else {}),
    )
    await async_session.commit()
    return _handoff_task(tasks), _non_handoff_task(tasks), candidate_session


__all__ = [name for name in globals() if not name.startswith("__")]
