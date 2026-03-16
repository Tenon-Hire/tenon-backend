from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.domains.common.base import APIModel
from app.domains.common.progress import ProgressSummary
from app.domains.common.types import CandidateSessionStatus
from app.domains.tasks.schemas_public import TaskPublic


class CandidateInviteRequest(APIModel):
    """Schema for inviting a candidate to a simulation."""

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


class CandidateSimulationSummary(APIModel):
    """Summary of the simulation for candidate session response."""

    id: int
    title: str
    role: str


class DayWindow(APIModel):
    """Daily availability window in UTC."""

    dayIndex: int
    windowStartAt: datetime
    windowEndAt: datetime


class CurrentDayWindow(DayWindow):
    """Derived current or nearest day window state."""

    state: Literal["upcoming", "active", "closed"]


class CandidateSessionResolveResponse(APIModel):
    """Schema for resolving a candidate session."""

    candidateSessionId: int
    status: CandidateSessionStatus
    claimedAt: datetime | None
    startedAt: datetime | None
    completedAt: datetime | None
    candidateName: str
    simulation: CandidateSimulationSummary
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


class CandidatePrivacyConsentRequest(APIModel):
    """Request payload for recording candidate media/privacy consent."""

    noticeVersion: str = Field(..., min_length=1, max_length=100)
    aiNoticeVersion: str | None = Field(default=None, min_length=1, max_length=100)


class CandidatePrivacyConsentResponse(APIModel):
    """Response payload for candidate privacy consent recording."""

    status: Literal["consent_recorded"]


class CandidateInviteListItem(APIModel):
    """Dashboard-friendly invite summary for candidates."""

    candidateSessionId: int
    simulationId: int
    simulationTitle: str
    role: str
    companyName: str | None
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


class CurrentTaskWindow(APIModel):
    """Window metadata for the current task day."""

    windowStartAt: datetime | None = None
    windowEndAt: datetime | None = None
    nextOpenAt: datetime | None = None
    isOpen: bool
    now: datetime


class CurrentTaskResponse(APIModel):
    """Schema for the current task assigned to the candidate."""

    candidateSessionId: int
    status: CandidateSessionStatus
    currentDayIndex: int | None
    currentTask: TaskPublic | None
    completedTaskIds: list[int]
    progress: ProgressSummary
    isComplete: bool
    currentWindow: CurrentTaskWindow | None = None


class CandidateSessionListItem(APIModel):
    """Schema for listing candidate sessions."""

    candidateSessionId: int
    inviteEmail: EmailStr
    candidateName: str
    status: CandidateSessionStatus
    startedAt: datetime | None
    completedAt: datetime | None
    hasFitProfile: bool
    inviteEmailStatus: str | None = None
    inviteEmailSentAt: datetime | None = None
    inviteEmailError: str | None = None
