"""Application module for submissions routes submissions routes submissions routes list routes workflows."""

from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import User
from app.submissions.presentation import present_list_item
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    TalentPartnerSubmissionListItemOut,
    TalentPartnerSubmissionListOut,
)
from app.submissions.services import (
    service_talent_partner as talent_partner_sub_service,
)

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get(
    "",
    response_model=TalentPartnerSubmissionListOut,
    response_model_exclude={"items": {"__all__": {"testResults": {"output"}}}},
)
async def list_submissions_route(
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    candidateSessionId: int | None = Query(default=None),
    taskId: int | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TalentPartnerSubmissionListOut:
    """List submissions visible to the Talent Partner with optional filters."""
    ensure_talent_partner(user)
    rows = await talent_partner_sub_service.list_submissions(
        db, user.id, candidateSessionId, taskId, limit, offset
    )
    parsed_rows: list[tuple[object, object]] = []
    for row in rows:
        sub = row
        task = None
        with suppress(TypeError, ValueError):
            sub, task, *_ = row
        if task is None:
            continue
        parsed_rows.append((sub, task))

    candidate_session_ids: set[int] = set()
    day_indexes: set[int] = set()
    for sub, task in parsed_rows:
        candidate_session_id = getattr(sub, "candidate_session_id", None)
        day_index = getattr(task, "day_index", None)
        if isinstance(candidate_session_id, int) and isinstance(day_index, int):
            candidate_session_ids.add(candidate_session_id)
            day_indexes.add(day_index)

    day_audits = await cs_repo.list_day_audits(
        db,
        candidate_session_ids=candidate_session_ids,
        day_indexes=day_indexes,
    )
    day_audit_by_key = {
        (audit.candidate_session_id, audit.day_index): audit for audit in day_audits
    }

    items: list[TalentPartnerSubmissionListItemOut] = []
    for sub, task in parsed_rows:
        day_audit = None
        candidate_session_id = getattr(sub, "candidate_session_id", None)
        day_index = getattr(task, "day_index", None)
        if isinstance(candidate_session_id, int) and isinstance(day_index, int):
            day_audit = day_audit_by_key.get((candidate_session_id, day_index))
        try:
            payload = present_list_item(sub, task, day_audit=day_audit)
        except TypeError:
            payload = present_list_item(sub, task)
        items.append(TalentPartnerSubmissionListItemOut(**payload))
    return TalentPartnerSubmissionListOut(items=items)
