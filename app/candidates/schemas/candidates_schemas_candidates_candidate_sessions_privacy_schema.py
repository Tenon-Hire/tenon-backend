"""Application module for candidates schemas candidates candidate sessions privacy schema workflows."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.shared.types.shared_types_base_model import APIModel


class CandidatePrivacyConsentRequest(APIModel):
    """Request payload for recording candidate media/privacy consent."""

    noticeVersion: str = Field(..., min_length=1, max_length=100)
    aiNoticeVersion: str | None = Field(default=None, min_length=1, max_length=100)


class CandidatePrivacyConsentResponse(APIModel):
    """Response payload for candidate privacy consent recording."""

    status: Literal["consent_recorded"]
