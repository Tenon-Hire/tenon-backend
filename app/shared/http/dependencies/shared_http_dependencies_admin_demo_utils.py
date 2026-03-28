"""Application module for http dependencies admin demo utils workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.auth.principal import bearer_scheme, get_principal
from app.shared.database import get_session
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_actor_utils import (
    DemoAdminActor,
)
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_rules_utils import (
    allowlist_contains_email,
    allowlist_contains_recruiter_id,
    allowlist_contains_subject,
    build_actor,
    is_admin_claim,
    lookup_recruiter_id,
)


async def require_demo_mode_admin(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> DemoAdminActor:
    """Require demo mode admin."""
    if not bool(settings.DEMO_MODE):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    principal = await get_principal(credentials, request)
    recruiter_id = await lookup_recruiter_id(db, email=principal.email)
    if is_admin_claim(principal):
        return build_actor(principal, recruiter_id)

    if (
        allowlist_contains_email(principal.email)
        or allowlist_contains_subject(principal.sub)
        or allowlist_contains_recruiter_id(recruiter_id)
    ):
        return build_actor(principal, recruiter_id)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )


__all__ = ["DemoAdminActor", "require_demo_mode_admin"]
