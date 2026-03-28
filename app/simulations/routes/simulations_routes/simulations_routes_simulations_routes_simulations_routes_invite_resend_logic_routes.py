"""Application module for simulations routes simulations routes simulations routes invite resend logic routes workflows."""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.services import service as notification_service
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.shared.database.shared_database_models_model import CandidateSession
from app.simulations import services as sim_service
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_rate_limits_routes import (
    enforce_invite_resend_limit,
)


async def resend_invite(
    *,
    simulation_id: int,
    candidate_session_id: int,
    request: Request,
    db: AsyncSession,
    user,
    email_service: EmailService,
) -> CandidateSession:
    """Resend invite."""
    ensure_recruiter_or_none(user)
    enforce_invite_resend_limit(request, user.id, candidate_session_id)

    sim = await sim_service.require_owned_simulation(db, simulation_id, user.id)
    sim_service.require_simulation_invitable(sim)
    cs: CandidateSession | None = await db.get(CandidateSession, candidate_session_id)
    if cs is None or cs.simulation_id != sim.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate session not found"
        )

    await notification_service.send_invite_email(
        db,
        candidate_session=cs,
        simulation=sim,
        invite_url=sim_service.invite_url(cs.token),
        email_service=email_service,
        now=None,
    )
    return cs


__all__ = ["resend_invite"]
