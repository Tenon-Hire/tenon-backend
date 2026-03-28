"""Application module for media services media privacy consent service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import CandidateSession

logger = logging.getLogger("app.media.services.media_services_media_privacy_service")


def _normalized_notice_version(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="noticeVersion is required",
        )
    return normalized


def require_media_consent(candidate_session: CandidateSession) -> None:
    """Require media consent."""
    if (
        not (candidate_session.consent_version or "").strip()
        or candidate_session.consent_timestamp is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent is required before upload completion",
        )


async def record_candidate_session_consent(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    notice_version: str,
    ai_notice_version: str | None = None,
) -> CandidateSession:
    """Record candidate session consent."""
    resolved_notice_version = _normalized_notice_version(notice_version)
    resolved_ai_notice_version = (
        (ai_notice_version or "").strip()
        or (getattr(candidate_session, "ai_notice_version", "") or "").strip()
        or resolved_notice_version
    )

    if (
        candidate_session.consent_version == resolved_notice_version
        and candidate_session.ai_notice_version == resolved_ai_notice_version
        and candidate_session.consent_timestamp is not None
    ):
        _log_consent(candidate_session)
        return candidate_session

    now = datetime.now(UTC)
    candidate_session.consent_version = resolved_notice_version
    candidate_session.consent_timestamp = now
    candidate_session.ai_notice_version = resolved_ai_notice_version
    await db.commit()
    await db.refresh(candidate_session)
    _log_consent(candidate_session)
    return candidate_session


def _log_consent(candidate_session: CandidateSession) -> None:
    logger.info(
        "consent recorded candidateSessionId=%s consentVersion=%s consentTimestamp=%s",
        candidate_session.id,
        candidate_session.consent_version,
        candidate_session.consent_timestamp.isoformat()
        if candidate_session.consent_timestamp
        else None,
    )
