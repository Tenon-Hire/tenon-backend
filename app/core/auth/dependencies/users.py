from __future__ import annotations

import sys

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.principal import Principal
from app.core.db import async_session_maker
from app.domains import User

from .db import lookup_user as lookup_user_default
from .modules import current_user_module


def _role_from_principal(principal: Principal) -> str:
    permissions = set(getattr(principal, "permissions", []) or [])
    roles = {str(r).lower() for r in (getattr(principal, "roles", []) or [])}
    if "candidate:access" in permissions or "candidate" in roles:
        return "candidate"
    return "recruiter"


async def user_from_principal(principal: Principal, db: AsyncSession | None) -> User:
    # Prefer injected db; fall back to session maker for backward-compat.
    if db is None:
        current_user_mod = current_user_module()
        maker = getattr(current_user_mod, "async_session_maker", async_session_maker)
        async with maker() as session:
            return await user_from_principal(principal, session)

    dep_module = sys.modules.get("app.core.auth.dependencies")
    lookup_user = getattr(dep_module, "_lookup_user", lookup_user_default)
    user = await lookup_user(db, principal.email)
    if user is None:
        user = User(
            name=principal.name or principal.email.split("@")[0],
            email=principal.email,
            role=_role_from_principal(principal),
            password_hash="",
        )
        db.add(user)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            user = await lookup_user(db, principal.email)
        else:
            await db.refresh(user)

    return user
