"""Application module for candidates schemas candidates candidate sessions invites schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_windows_schema import (
    CurrentDayWindow,
    DayWindow,
)
from app.shared.types.shared_types_base_model import APIModel
from app.shared.types.shared_types_progress_model import ProgressSummary
from app.shared.types.shared_types_types_model import CandidateSessionStatus


class CandidateInviteRequest(APIModel):
    """Schema for inviting a candidate to a trial."""

    candidateName: str = Field(..., min_length=1, max_length=255)
    inviteEmail: EmailStr


class CandidateInviteResponse(APIModel):
    """Schema for the response after inviting a candidate."""

    candidateSessionId: int
    token: str
    inviteUrl: str
    outcome: Literal["created", "resent"]


class CandidateInviteError(APIModel):
    """Schema for rejected invite errors."""

    code: str
    message: str
    outcome: Literal["rejected"]


class CandidateInviteErrorResponse(APIModel):
    """Schema for invite error responses."""

    error: CandidateInviteError


class CandidateInviteListItem(APIModel):
    """Dashboard-friendly invite summary for candidates."""

    candidateSessionId: int
    trialId: int
    trialTitle: str
    role: str
    companyName: str | None
    talentPartnerName: str | None = None
    talentPartnerEmail: str | None = None
    status: CandidateSessionStatus
    progress: ProgressSummary
    lastActivityAt: datetime | None
    inviteCreatedAt: datetime | None
    expiresAt: datetime | None
    inviteToken: str | None = None
    isExpired: bool
    scheduledStartAt: datetime | None = None
    candidateTimezone: str | None = None
    dayWindows: list[DayWindow] = Field(default_factory=list)
    scheduleLockedAt: datetime | None = None
    currentDayWindow: CurrentDayWindow | None = None
