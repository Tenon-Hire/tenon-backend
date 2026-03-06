from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.candidate_sessions import candidate_session_from_headers
from app.core.db import get_session
from app.core.errors import (
    DRAFT_FINALIZED,
    DRAFT_NOT_FOUND,
    ApiError,
)
from app.domains import CandidateSession
from app.domains.candidate_sessions import service as cs_service
from app.domains.submissions import service_candidate as submission_service
from app.repositories.task_drafts import repository as task_drafts_repo
from app.schemas.task_drafts import (
    TaskDraftResponse,
    TaskDraftUpsertRequest,
    TaskDraftUpsertResponse,
)
from app.services.task_drafts import validate_draft_payload_size

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{task_id}/draft",
    response_model=TaskDraftResponse,
)
async def get_task_draft_route(
    task_id: Annotated[int, Path(..., ge=1)],
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskDraftResponse:
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)

    draft = await task_drafts_repo.get_by_session_and_task(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    if draft is None:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
            error_code=DRAFT_NOT_FOUND,
            retryable=False,
        )

    return TaskDraftResponse(
        taskId=task.id,
        contentText=draft.content_text,
        contentJson=draft.content_json,
        updatedAt=draft.updated_at,
        finalizedAt=draft.finalized_at,
        finalizedSubmissionId=draft.finalized_submission_id,
    )


@router.put(
    "/{task_id}/draft",
    response_model=TaskDraftUpsertResponse,
)
async def put_task_draft_route(
    task_id: Annotated[int, Path(..., ge=1)],
    payload: TaskDraftUpsertRequest,
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskDraftUpsertResponse:
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)

    cs_service.require_active_window(candidate_session, task)

    if await submission_service.submissions_repo.find_duplicate(
        db, candidate_session.id, task.id
    ):
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task is already finalized.",
            error_code=DRAFT_FINALIZED,
            retryable=False,
        )

    text_bytes, json_bytes = validate_draft_payload_size(
        content_text=payload.contentText,
        content_json=payload.contentJson,
    )

    try:
        draft = await task_drafts_repo.upsert_draft(
            db,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            content_text=payload.contentText,
            content_json=payload.contentJson,
        )
    except task_drafts_repo.TaskDraftFinalizedError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task draft is finalized and cannot be updated.",
            error_code=DRAFT_FINALIZED,
            retryable=False,
        ) from exc

    logger.info(
        "Task draft upsert candidateSessionId=%s taskId=%s textBytes=%s jsonBytes=%s",
        candidate_session.id,
        task.id,
        text_bytes,
        json_bytes,
    )

    return TaskDraftUpsertResponse(taskId=task.id, updatedAt=draft.updated_at)


__all__ = ["router", "get_task_draft_route", "put_task_draft_route"]
