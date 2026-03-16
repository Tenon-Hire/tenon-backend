from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.candidate_access import require_candidate_principal
from app.core.auth.principal import Principal
from app.core.db import get_session
from app.domains.candidate_sessions import service as cs_service
from app.domains.candidate_sessions.schemas import (
    CandidatePrivacyConsentRequest,
    CandidatePrivacyConsentResponse,
)
from app.services.media.privacy import record_candidate_session_consent

router = APIRouter()


@router.post(
    "/session/{candidate_session_id}/privacy/consent",
    response_model=CandidatePrivacyConsentResponse,
    status_code=status.HTTP_200_OK,
)
async def record_candidate_privacy_consent(
    candidate_session_id: Annotated[int, Path(..., ge=1)],
    payload: CandidatePrivacyConsentRequest,
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CandidatePrivacyConsentResponse:
    candidate_session = await cs_service.fetch_owned_session(
        db,
        candidate_session_id,
        principal,
        now=datetime.now(UTC),
    )
    await record_candidate_session_consent(
        db,
        candidate_session=candidate_session,
        notice_version=payload.noticeVersion,
        ai_notice_version=payload.aiNoticeVersion,
    )
    return CandidatePrivacyConsentResponse(status="consent_recorded")


__all__ = ["record_candidate_privacy_consent", "router"]
