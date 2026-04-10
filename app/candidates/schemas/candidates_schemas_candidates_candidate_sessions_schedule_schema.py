"""Application module for candidates schemas candidates candidate sessions schedule schema workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_windows_schema import (
    CandidateTrialSummary,
    CurrentDayWindow,
    DayWindow,
)
from app.shared.types.shared_types_base_model import APIModel
from app.shared.types.shared_types_types_model import CandidateSessionStatus


class CandidateSessionResolveResponse(APIModel):
    """Schema for resolving a candidate session."""

    candidateSessionId: int
    status: CandidateSessionStatus
    claimedAt: datetime | None
    startedAt: datetime | None
    completedAt: datetime | None
    candidateName: str
    trial: CandidateTrialSummary
    aiNoticeText: str
    aiNoticeVersion: str
    evalEnabledByDay: dict[str, bool]
    startAt: datetime | None = None
    windowStartAt: datetime | None = None
    windowEndAt: datetime | None = None
    scheduledStartAt: datetime | None = None
    candidateTimezone: str | None = None
    dayWindows: list[DayWindow] = Field(default_factory=list)
    scheduleLockedAt: datetime | None = None
    currentDayWindow: CurrentDayWindow | None = None


class CandidateSessionScheduleRequest(APIModel):
    """Request payload for scheduling a candidate session."""

    scheduledStartAt: datetime
    candidateTimezone: str = Field(..., min_length=1, max_length=255)


class CandidateSessionScheduleResponse(APIModel):
    """Response payload for scheduling a candidate session."""

    candidateSessionId: int
    scheduledStartAt: datetime
    candidateTimezone: str
    dayWindows: list[DayWindow]
    scheduleLockedAt: datetime
