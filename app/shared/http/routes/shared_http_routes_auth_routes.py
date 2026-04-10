"""Application module for http routes auth routes workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth import rate_limit
from app.shared.auth.shared_auth_current_user_utils import (
    get_authenticated_user,
    get_current_user,
)
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import Company, User
from app.talent_partners.schemas.talent_partners_schemas_talent_partners_users_schema import (
    TalentPartnerOnboardingWrite,
    UserRead,
)

router = APIRouter()

AUTH_ME_RATE_LIMIT = rate_limit.RateLimitRule(limit=60, window_seconds=60.0)
MAX_USER_NAME_CHARS = 200
MAX_COMPANY_NAME_CHARS = 255


def _normalize_required_text(
    value: str | None, *, field_name: str, max_chars: int
) -> str:
    normalized = " ".join((value or "").split())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} is required",
        )
    if len(normalized) > max_chars:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be at most {max_chars} characters",
        )
    return normalized


async def _get_company_name(db: AsyncSession, company_id: int | None) -> str | None:
    if company_id is None:
        return None
    return await db.scalar(select(Company.name).where(Company.id == company_id))


def _build_user_read(user: User, company_name: str | None) -> UserRead:
    onboarding_complete = (
        getattr(user, "role", None) != "talent_partner"
        or getattr(user, "company_id", None) is not None
    )
    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        companyId=getattr(user, "company_id", None),
        companyName=company_name,
        onboardingComplete=onboarding_complete,
    )


async def _create_or_get_company(db: AsyncSession, company_name: str) -> Company:
    existing = await db.scalar(select(Company).where(Company.name == company_name))
    if existing is not None:
        return existing

    company = Company(name=company_name)
    try:
        async with db.begin_nested():
            db.add(company)
            await db.flush()
    except IntegrityError:
        existing = await db.scalar(select(Company).where(Company.name == company_name))
        if existing is None:
            raise
        return existing
    return company


@router.get(
    "/me",
    response_model=UserRead,
    summary="Read Me",
    description="Return the authenticated Talent Partner profile for the caller.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Rate limit exceeded."},
    },
)
async def read_me(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_authenticated_user)],
) -> UserRead:
    """Return the currently authenticated user."""
    if rate_limit.rate_limit_enabled():
        key = rate_limit.rate_limit_key("auth_me", rate_limit.client_id(request))
        rate_limit.limiter.allow(key, AUTH_ME_RATE_LIMIT)
    company_name = await _get_company_name(
        db, getattr(current_user, "company_id", None)
    )
    return _build_user_read(current_user, company_name)


@router.post(
    "/talent-partner-onboarding",
    response_model=UserRead,
    summary="Complete TalentPartner Onboarding",
    description="Create or attach the Talent Partner's company and finalize app onboarding.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Invalid onboarding payload."
        },
    },
)
async def complete_talent_partner_onboarding(
    payload: TalentPartnerOnboardingWrite,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Finalize Talent Partner onboarding with name and company assignment."""
    if getattr(current_user, "role", None) != "talent_partner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Talent Partner access required",
        )

    talent_partner_name = _normalize_required_text(
        payload.name,
        field_name="name",
        max_chars=MAX_USER_NAME_CHARS,
    )
    company_name = _normalize_required_text(
        payload.companyName,
        field_name="companyName",
        max_chars=MAX_COMPANY_NAME_CHARS,
    )

    company = await _create_or_get_company(db, company_name)
    current_user.name = talent_partner_name
    current_user.company_id = company.id
    await db.commit()
    await db.refresh(current_user)
    return _build_user_read(current_user, company.name)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description=(
        "Stateless logout acknowledgment endpoint; client clears local auth" " state."
    ),
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected logout response failure."
        }
    },
)
async def logout() -> Response:
    """Stateless logout endpoint; backend does not manage sessions or redirects."""
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )
