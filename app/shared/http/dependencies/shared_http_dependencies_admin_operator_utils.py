"""Admin/operator authorization dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.dependencies import dev_bypass_user
from app.shared.auth.principal import Principal, bearer_scheme, get_principal
from app.shared.database import get_session
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_actor_utils import (
    DemoAdminActor,
)
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_rules_utils import (
    build_actor,
    is_admin_claim,
    lookup_talent_partner_id,
)


def _principal_from_dev_admin_user(user: object) -> Principal:
    email = str(getattr(user, "email", "") or "").strip().lower()
    name = str(getattr(user, "name", "") or "").strip() or email
    sub = f"dev-admin:{email}"
    return Principal(
        sub=sub,
        email=email,
        name=name,
        roles=["admin"],
        permissions=[],
        claims={"sub": sub, "email": email, "roles": ["admin"], "name": name},
    )


async def require_operator_admin(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> DemoAdminActor:
    """Require an authenticated admin/operator principal."""
    dev_user = await dev_bypass_user(request, db)
    if dev_user is not None:
        if getattr(dev_user, "role", None) != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        principal = _principal_from_dev_admin_user(dev_user)
        return build_actor(principal, None)

    principal = await get_principal(credentials, request)
    if not is_admin_claim(principal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    talent_partner_id = await lookup_talent_partner_id(db, email=principal.email)
    return build_actor(principal, talent_partner_id)


__all__ = ["DemoAdminActor", "require_operator_admin"]
