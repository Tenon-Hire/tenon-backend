"""Application module for Talent Partner company AI-config routes workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import PROMPT_PACK_VERSION, normalize_prompt_override_payload
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import Company, User
from app.talent_partners.schemas.talent_partners_schemas_talent_partners_company_ai_config_schema import (
    CompanyAIConfigRead,
    CompanyAIConfigWrite,
)

router = APIRouter(prefix="/companies")


async def _require_talent_partner_company(
    db: AsyncSession,
    current_user: User,
) -> Company:
    ensure_talent_partner(current_user)
    company_id = getattr(current_user, "company_id", None)
    company = await db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return company


def _render_company_ai_config(company: Company) -> CompanyAIConfigRead:
    return CompanyAIConfigRead(
        companyId=company.id,
        companyName=company.name,
        promptPackVersion=PROMPT_PACK_VERSION,
        promptOverrides=getattr(company, "ai_prompt_overrides_json", None),
    )


@router.get(
    "/me/ai-config",
    response_model=CompanyAIConfigRead,
    summary="Read TalentPartner Company AI Config",
)
async def read_company_ai_config(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CompanyAIConfigRead:
    """Return Talent Partner company AI override defaults."""
    company = await _require_talent_partner_company(db, current_user)
    return _render_company_ai_config(company)


@router.put(
    "/me/ai-config",
    response_model=CompanyAIConfigRead,
    summary="Update TalentPartner Company AI Config",
)
async def update_company_ai_config(
    payload: CompanyAIConfigWrite,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CompanyAIConfigRead:
    """Replace Talent Partner company AI override defaults."""
    company = await _require_talent_partner_company(db, current_user)
    company.ai_prompt_overrides_json = normalize_prompt_override_payload(
        payload.promptOverrides
    )
    await db.commit()
    await db.refresh(company)
    return _render_company_ai_config(company)


__all__ = ["router"]
