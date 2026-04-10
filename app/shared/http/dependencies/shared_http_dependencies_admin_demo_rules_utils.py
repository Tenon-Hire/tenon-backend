"""Application module for http dependencies admin demo rules utils workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import User
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_actor_utils import (
    DemoAdminActor,
)
from app.shared.utils.shared_utils_normalization_utils import (
    normalize_email as _normalize_email,
)


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


def is_admin_claim(principal: Principal) -> bool:
    """Return whether admin claim."""
    claims = principal.claims or {}
    role_tokens: list[str] = []
    role_tokens.extend(_normalized_tokens(principal.roles))
    role_tokens.extend(_normalized_tokens(claims.get("role")))
    role_tokens.extend(_normalized_tokens(claims.get("roles")))
    role_tokens.extend(_normalized_tokens(claims.get("winoe_roles")))
    role_tokens.extend(_normalized_tokens(claims.get(settings.auth.AUTH0_ROLES_CLAIM)))
    return "admin" in role_tokens


def _normalize_subject(value: str | None) -> str:
    return (value or "").strip()


async def lookup_talent_partner_id(db: AsyncSession, *, email: str) -> int | None:
    """Look up Talent Partner id."""
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None
    return (
        await db.execute(
            select(User.id).where(func.lower(User.email) == normalized_email)
        )
    ).scalar_one_or_none()


def allowlist_contains_email(email: str) -> bool:
    """Execute allowlist contains email."""
    allowed = {
        _normalize_email(value)
        for value in settings.DEMO_ADMIN_ALLOWLIST_EMAILS or []
        if isinstance(value, str) and value.strip()
    }
    normalized_email = _normalize_email(email)
    return bool(normalized_email and normalized_email in allowed)


def allowlist_contains_subject(subject: str) -> bool:
    """Execute allowlist contains subject."""
    allowed = {
        _normalize_subject(value)
        for value in settings.DEMO_ADMIN_ALLOWLIST_SUBJECTS or []
        if isinstance(value, str) and value.strip()
    }
    normalized_subject = _normalize_subject(subject)
    return bool(normalized_subject and normalized_subject in allowed)


def allowlist_contains_talent_partner_id(talent_partner_id: int | None) -> bool:
    """Execute allowlist contains Talent Partner id."""
    if talent_partner_id is None:
        return False
    return talent_partner_id in set(
        settings.DEMO_ADMIN_ALLOWLIST_TALENT_PARTNER_IDS or []
    )


def build_actor(principal: Principal, talent_partner_id: int | None) -> DemoAdminActor:
    """Build actor."""
    if talent_partner_id is not None:
        return DemoAdminActor(
            principal=principal,
            actor_type="talent_partner_admin",
            actor_id=str(talent_partner_id),
            talent_partner_id=talent_partner_id,
        )
    return DemoAdminActor(
        principal=principal,
        actor_type="principal_admin",
        actor_id=_normalize_subject(principal.sub),
        talent_partner_id=None,
    )
