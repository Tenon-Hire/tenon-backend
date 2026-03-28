"""Application module for auth dependencies current user utils workflows."""

from __future__ import annotations

import sys
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.principal import bearer_scheme, get_principal
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import User

from .shared_auth_dependencies_dev_bypass_utils import dev_bypass_user
from .shared_auth_dependencies_users_utils import user_from_principal


async def _resolve_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    *,
    require_recruiter: bool,
) -> User:
    """Resolve the current user via dev bypass (local/test) or Auth0 JWT."""
    dep_module = sys.modules.get("app.shared.auth.dependencies")
    dev_bypass = getattr(dep_module, "_dev_bypass_user", dev_bypass_user)
    user_loader = getattr(dep_module, "_user_from_principal", user_from_principal)

    dev_user = await dev_bypass(request, db)
    if dev_user:
        return dev_user

    principal = await get_principal(credentials, request)
    if require_recruiter and "recruiter:access" not in principal.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter access required",
        )

    return await user_loader(principal, db)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Return the current recruiter-facing user."""
    return await _resolve_current_user(request, db, credentials, require_recruiter=True)


async def get_authenticated_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Return any authenticated user (recruiter or candidate)."""
    return await _resolve_current_user(
        request, db, credentials, require_recruiter=False
    )
