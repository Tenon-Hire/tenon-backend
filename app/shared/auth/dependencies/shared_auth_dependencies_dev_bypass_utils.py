"""Application module for auth dependencies dev bypass utils workflows."""

from __future__ import annotations

import sys

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.database import async_session_maker

from .shared_auth_dependencies_db_utils import lookup_user as lookup_user_default
from .shared_auth_dependencies_env_utils import env_name
from .shared_auth_dependencies_modules_utils import current_user_module


async def dev_bypass_user(request: Request, db: AsyncSession | None):
    """Allow local dev bypass when enabled and header present."""
    dev_email = (request.headers.get("x-dev-user-email") or "").strip().lower()
    if not dev_email:
        return None
    dev_bypass_env = settings.dev_auth_bypass_enabled

    dep_module = sys.modules.get("app.shared.auth.dependencies")
    env = getattr(dep_module, "_env_name", env_name)()
    if dev_bypass_env and env != "local":
        raise RuntimeError("DEV_AUTH_BYPASS must never be enabled outside ENV=local")
    if env not in {"local", "test"} and not dev_bypass_env:
        return None

    client_host = (getattr(request.client, "host", "") or "").lower()
    is_localhost = client_host in {
        "127.0.0.1",
        "::1",
        "localhost",
    } or client_host.startswith("::ffff:127.0.0.1")
    if not is_localhost:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DEV_AUTH_BYPASS only allowed from localhost",
        )

    if db is None:
        current_user_mod = current_user_module()
        maker = getattr(current_user_mod, "async_session_maker", async_session_maker)
        async with maker() as session:
            return await dev_bypass_user(request, session)

    lookup_user = getattr(dep_module, "_lookup_user", lookup_user_default)
    user = await lookup_user(db, dev_email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Dev user not found: {dev_email}",
        )
    return user
