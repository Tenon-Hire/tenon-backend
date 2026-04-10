"""Application module for auth dependencies users utils workflows."""

from __future__ import annotations

import sys

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.principal import Principal
from app.shared.database import async_session_maker
from app.shared.database.shared_database_models_model import User

from .shared_auth_dependencies_db_utils import lookup_user as lookup_user_default
from .shared_auth_dependencies_env_utils import env_name
from .shared_auth_dependencies_local_talent_partner_company_utils import (
    ensure_local_talent_partner_company,
)
from .shared_auth_dependencies_modules_utils import current_user_module


def _role_from_principal(principal: Principal) -> str:
    permissions = set(getattr(principal, "permissions", []) or [])
    roles = {str(r).lower() for r in (getattr(principal, "roles", []) or [])}
    if "candidate:access" in permissions or "candidate" in roles:
        return "candidate"
    return "talent_partner"


async def _resolve_local_company_id(
    db: AsyncSession, *, email: str, role: str, company_id: int | None
) -> int | None:
    normalized_email = (email or "").strip().lower()
    if (
        role != "talent_partner"
        or company_id is not None
        or env_name() != "local"
        or not normalized_email.endswith("@local.test")
    ):
        return company_id
    company = await ensure_local_talent_partner_company(db)
    return company.id


async def user_from_principal(principal: Principal, db: AsyncSession | None) -> User:
    # Prefer injected db; fall back to session maker for backward-compat.
    """Execute user from principal."""
    if db is None:
        current_user_mod = current_user_module()
        maker = getattr(current_user_mod, "async_session_maker", async_session_maker)
        async with maker() as session:
            return await user_from_principal(principal, session)

    dep_module = sys.modules.get("app.shared.auth.dependencies")
    lookup_user = getattr(dep_module, "_lookup_user", lookup_user_default)
    user = await lookup_user(db, principal.email)
    if user is None:
        role = _role_from_principal(principal)
        user = User(
            name=principal.name or principal.email.split("@")[0],
            email=principal.email,
            role=role,
            company_id=await _resolve_local_company_id(
                db,
                email=principal.email,
                role=role,
                company_id=None,
            ),
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
    else:
        resolved_company_id = await _resolve_local_company_id(
            db,
            email=getattr(user, "email", ""),
            role=getattr(user, "role", ""),
            company_id=getattr(user, "company_id", None),
        )
        if resolved_company_id != getattr(user, "company_id", None):
            user.company_id = resolved_company_id
            await db.commit()
            await db.refresh(user)

    return user
