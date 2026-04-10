"""Application module for trials routes trials routes trials routes candidates routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateSessionListItem,
)
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.shared.database import get_session
from app.shared.types.shared_types_progress_model import ProgressSummary
from app.trials import services as sim_service
from app.trials.services.trials_services_trials_candidates_compare_day_completion_service import (
    load_day_completion,
)
from app.trials.services.trials_services_trials_urls_service import (
    invite_url,
)

router = APIRouter()


@router.get(
    "/{trial_id}/candidates",
    response_model=list[CandidateSessionListItem],
    status_code=status.HTTP_200_OK,
)
async def list_trial_candidates(
    trial_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
    includeTerminated: bool = False,
):
    """List candidate sessions for a trial (Talent Partner-only)."""
    ensure_talent_partner_or_none(user)
    await sim_service.require_owned_trial(
        db,
        trial_id,
        user.id,
        include_terminated=includeTerminated,
    )
    rows = await sim_service.list_candidates_with_profile(db, trial_id)
    session_ids = [cs.id for cs, _ in rows]
    day_completion_by_session: dict[int, dict[str, bool]] = {}
    if session_ids and hasattr(db, "execute"):
        day_completion_by_session, _ = await load_day_completion(
            db,
            trial_id=trial_id,
            candidate_session_ids=session_ids,
        )
    return [
        CandidateSessionListItem(
            candidateSessionId=cs.id,
            inviteEmail=cs.invite_email,
            candidateName=cs.candidate_name,
            status=cs.status,
            startedAt=cs.started_at,
            completedAt=cs.completed_at,
            hasWinoeReport=(profile_id is not None),
            hasReport=(profile_id is not None),
            reportReady=(profile_id is not None),
            reportId=str(profile_id) if profile_id is not None else None,
            dayProgress=ProgressSummary(
                completed=sum(
                    1
                    for completed in day_completion_by_session.get(cs.id, {}).values()
                    if completed
                ),
                total=len(day_completion_by_session.get(cs.id, {})) or 5,
            ),
            inviteToken=(token := getattr(cs, "token", None)),
            inviteUrl=invite_url(token) if token else None,
            inviteEmailStatus=getattr(cs, "invite_email_status", None),
            inviteEmailSentAt=getattr(cs, "invite_email_sent_at", None),
            inviteEmailError=getattr(cs, "invite_email_error", None),
        )
        for cs, profile_id in rows
    ]
