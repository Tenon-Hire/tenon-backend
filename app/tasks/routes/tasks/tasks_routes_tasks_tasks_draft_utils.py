"""Application module for tasks routes tasks draft utils workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.shared.database.shared_database_models_model import CandidateSession
from app.submissions.schemas.submissions_schemas_submissions_task_drafts_schema import (
    TaskDraftResponse,
    TaskDraftUpsertResponse,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)


def coerce_utc_datetime(value: datetime | None) -> datetime | None:
    """Execute coerce utc datetime."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def build_draft_response(task_id: int, draft: Any) -> TaskDraftResponse:
    """Build draft response."""
    return TaskDraftResponse(
        taskId=task_id,
        contentText=draft.content_text,
        contentJson=draft.content_json,
        updatedAt=coerce_utc_datetime(draft.updated_at),
        finalizedAt=coerce_utc_datetime(draft.finalized_at),
        finalizedSubmissionId=draft.finalized_submission_id,
    )


def build_upsert_response(task_id: int, draft: Any) -> TaskDraftUpsertResponse:
    """Build upsert response."""
    return TaskDraftUpsertResponse(
        taskId=task_id,
        updatedAt=coerce_utc_datetime(draft.updated_at),
    )


async def resolve_task_and_duplicate(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
) -> tuple[Any, bool]:
    """Resolve task and duplicate."""
    try:
        task_list, completed_ids, *_ = await cs_service.progress_snapshot(
            db, candidate_session
        )
        task = next((item for item in task_list if item.id == task_id), None)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        return task, task.id in completed_ids
    except (AttributeError, TypeError):
        task = await submission_service.load_task_or_404(db, task_id)
        submission_service.ensure_task_belongs(task, candidate_session)
        duplicate = await submission_service.submissions_repo.find_duplicate(
            db, candidate_session.id, task.id
        )
        return task, duplicate
