"""Application module for candidates routes candidate sessions routes candidates candidate sessions routes claim logic routes workflows."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_rate_limits_routes import (
    rate_limit_claim,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_time_utils import (
    utcnow,
)
from app.shared.auth.principal import Principal


async def claim_token(
    token: str, request: Request, principal: Principal, db: AsyncSession
):
    """Claim token."""
    rate_limit_claim(request, token)
    return await cs_service.claim_invite_with_principal(
        db, token, principal, now=utcnow()
    )


__all__ = ["claim_token"]
