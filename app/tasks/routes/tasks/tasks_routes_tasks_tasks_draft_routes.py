"""Application module for tasks routes tasks draft routes workflows."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils import (
    candidate_session_from_headers,
)
from app.shared.utils.shared_utils_errors_utils import (
    DRAFT_FINALIZED,
    DRAFT_NOT_FOUND,
    ApiError,
)
from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from app.submissions.schemas.submissions_schemas_submissions_task_drafts_schema import (
    TaskDraftResponse,
    TaskDraftUpsertRequest,
    TaskDraftUpsertResponse,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.task_drafts import validate_draft_payload_size
from app.tasks.routes.tasks.tasks_routes_tasks_tasks_draft_utils import (
    build_draft_response,
    build_upsert_response,
    resolve_task_and_duplicate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{task_id}/draft",
    response_model=TaskDraftResponse,
    summary="Get Task Draft Route",
    description=(
        "Return the saved draft payload for a candidate task in the current"
        " session context."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Draft or task not found."},
        status.HTTP_409_CONFLICT: {"description": "Task draft is finalized."},
    },
)
async def get_task_draft_route(
    task_id: Annotated[int, Path(..., ge=1)],
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskDraftResponse:
    """Handle the get task draft API route."""
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
    return build_draft_response(task.id, draft)


@router.put(
    "/{task_id}/draft",
    response_model=TaskDraftUpsertResponse,
    summary="Put Task Draft Route",
    description=(
        "Create or update a candidate task draft while enforcing active-window"
        " and finalization constraints."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Task not found."},
        status.HTTP_409_CONFLICT: {"description": "Task draft is finalized."},
    },
)
async def put_task_draft_route(
    task_id: Annotated[int, Path(..., ge=1)],
    payload: TaskDraftUpsertRequest,
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskDraftUpsertResponse:
    """Handle the put task draft API route."""
    task, duplicate_submission = await resolve_task_and_duplicate(
        db,
        candidate_session=candidate_session,
        task_id=task_id,
    )
    cs_service.require_active_window(candidate_session, task)
    if duplicate_submission:
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
            commit=False,
        )
    except task_drafts_repo.TaskDraftFinalizedError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task draft is finalized and cannot be updated.",
            error_code=DRAFT_FINALIZED,
            retryable=False,
        ) from exc
    if hasattr(db, "commit"):
        await db.commit()

    logger.info(
        "Task draft upsert candidateSessionId=%s taskId=%s textBytes=%s jsonBytes=%s",
        candidate_session.id,
        task.id,
        text_bytes,
        json_bytes,
    )
    return build_upsert_response(task.id, draft)


__all__ = ["router", "get_task_draft_route", "put_task_draft_route"]
