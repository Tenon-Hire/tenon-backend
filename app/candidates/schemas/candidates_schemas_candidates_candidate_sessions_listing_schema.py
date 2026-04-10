"""Application module for candidates schemas candidates candidate sessions listing schema workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr

from app.shared.types.shared_types_base_model import APIModel
from app.shared.types.shared_types_progress_model import ProgressSummary
from app.shared.types.shared_types_types_model import CandidateSessionStatus


class CandidateSessionListItem(APIModel):
    """Schema for listing candidate sessions."""

    candidateSessionId: int
    inviteEmail: EmailStr
    candidateName: str
    status: CandidateSessionStatus
    startedAt: datetime | None
    completedAt: datetime | None
    hasWinoeReport: bool
    hasReport: bool = False
    reportReady: bool | None = None
    reportId: str | None = None
    dayProgress: ProgressSummary | None = None
    inviteToken: str | None = None
    inviteUrl: str | None = None
    inviteEmailStatus: str | None = None
    inviteEmailSentAt: datetime | None = None
    inviteEmailError: str | None = None
