"""Application module for trials routes trials routes trials routes invite resend routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.shared.database import get_session
from app.shared.http.dependencies.shared_http_dependencies_notifications_utils import (
    get_email_service,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_invite_render_routes import (
    render_invite_status,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_invite_resend_logic_routes import (
    resend_invite,
)

router = APIRouter()


@router.post(
    "/{trial_id}/candidates/{candidate_session_id}/invite/resend",
    status_code=status.HTTP_200_OK,
    summary="Resend Candidate Invite",
    description=(
        "Resend an existing candidate invite email for a Talent Partner-owned"
        " trial session."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {
            "description": "Trial or candidate session not found."
        },
    },
)
async def resend_candidate_invite(
    trial_id: int,
    candidate_session_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
):
    """Resend candidate invite."""
    ensure_talent_partner_or_none(user)
    cs = await resend_invite(
        trial_id=trial_id,
        candidate_session_id=candidate_session_id,
        request=request,
        db=db,
        user=user,
        email_service=email_service,
    )
    return render_invite_status(cs)
