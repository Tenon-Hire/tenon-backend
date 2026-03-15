from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.principal import Principal, bearer_scheme, get_principal
from app.core.db import get_session
from app.core.settings import settings
from app.domains import User


@dataclass(frozen=True, slots=True)
class DemoAdminActor:
    principal: Principal
    actor_type: str
    actor_id: str
    recruiter_id: int | None


def _normalized_tokens(value: Any) -> list[str]:
    if isinstance(value, str):
        normalized = value.strip().lower()
        return [normalized] if normalized else []
    if isinstance(value, list):
        tokens: list[str] = []
        for item in value:
            if isinstance(item, str):
                normalized = item.strip().lower()
                if normalized:
                    tokens.append(normalized)
        return tokens
    return []


def _is_admin_claim(principal: Principal) -> bool:
    claims = principal.claims or {}
    role_tokens: list[str] = []
    role_tokens.extend(_normalized_tokens(principal.roles))
    role_tokens.extend(_normalized_tokens(claims.get("role")))
    role_tokens.extend(_normalized_tokens(claims.get("roles")))
    role_tokens.extend(_normalized_tokens(claims.get("tenon_roles")))
    role_tokens.extend(_normalized_tokens(claims.get(settings.auth.AUTH0_ROLES_CLAIM)))
    return "admin" in role_tokens


def _normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_subject(value: str | None) -> str:
    return (value or "").strip()


async def _lookup_recruiter_id(
    db: AsyncSession,
    *,
    email: str,
) -> int | None:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None
    return (
        await db.execute(
            select(User.id).where(func.lower(User.email) == normalized_email)
        )
    ).scalar_one_or_none()


def _allowlist_contains_email(email: str) -> bool:
    allowed = {
        _normalize_email(value)
        for value in settings.DEMO_ADMIN_ALLOWLIST_EMAILS or []
        if isinstance(value, str) and value.strip()
    }
    normalized_email = _normalize_email(email)
    return bool(normalized_email and normalized_email in allowed)


def _allowlist_contains_subject(subject: str) -> bool:
    allowed = {
        _normalize_subject(value)
        for value in settings.DEMO_ADMIN_ALLOWLIST_SUBJECTS or []
        if isinstance(value, str) and value.strip()
    }
    normalized_subject = _normalize_subject(subject)
    return bool(normalized_subject and normalized_subject in allowed)


def _allowlist_contains_recruiter_id(recruiter_id: int | None) -> bool:
    if recruiter_id is None:
        return False
    return recruiter_id in set(settings.DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS or [])


def _build_actor(principal: Principal, recruiter_id: int | None) -> DemoAdminActor:
    if recruiter_id is not None:
        return DemoAdminActor(
            principal=principal,
            actor_type="recruiter_admin",
            actor_id=str(recruiter_id),
            recruiter_id=recruiter_id,
        )
    return DemoAdminActor(
        principal=principal,
        actor_type="principal_admin",
        actor_id=_normalize_subject(principal.sub),
        recruiter_id=None,
    )


async def require_demo_mode_admin(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> DemoAdminActor:
    if not bool(settings.DEMO_MODE):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    principal = await get_principal(credentials, request)
    recruiter_id = await _lookup_recruiter_id(db, email=principal.email)
    if _is_admin_claim(principal):
        return _build_actor(principal, recruiter_id)

    if (
        _allowlist_contains_email(principal.email)
        or _allowlist_contains_subject(principal.sub)
        or _allowlist_contains_recruiter_id(recruiter_id)
    ):
        return _build_actor(principal, recruiter_id)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )


__all__ = ["DemoAdminActor", "require_demo_mode_admin"]
