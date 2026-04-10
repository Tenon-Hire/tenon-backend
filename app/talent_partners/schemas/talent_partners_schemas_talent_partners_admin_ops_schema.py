"""Application module for Talent Partners schemas Talent Partners admin ops schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_windows_schema import (
    CurrentDayWindow,
    DayWindow,
)
from app.shared.types.shared_types_base_model import APIModel

AdminResetTargetState = Literal["not_started", "claimed", "in_progress"]
AdminApplyTo = Literal["future_invites_only"]


class CandidateSessionResetRequest(APIModel):
    """Represent candidate session reset request data and behavior."""

    targetState: AdminResetTargetState
    reason: str = Field(..., min_length=3, max_length=500)
    overrideIfEvaluated: bool = False
    dryRun: bool = False


class CandidateSessionResetResponse(APIModel):
    """Represent candidate session reset response data and behavior."""

    candidateSessionId: int
    status: Literal["ok", "dry_run"]
    resetTo: AdminResetTargetState
    auditId: str | None = None


class CandidateSessionDayWindowControlRequest(APIModel):
    """Represent candidate-session dev day-window control request data and behavior."""

    targetDayIndex: int = Field(..., ge=1, le=5)
    reason: str = Field(..., min_length=3, max_length=500)
    candidateTimezone: str | None = Field(default=None, min_length=1, max_length=255)
    minutesAlreadyOpen: int = Field(default=15, ge=0, le=720)
    minutesUntilCutoff: int = Field(default=60, ge=1, le=720)
    windowStartLocal: str | None = Field(default=None)
    windowEndLocal: str | None = Field(default=None)
    dryRun: bool = False


class CandidateSessionDayWindowControlResponse(APIModel):
    """Represent candidate-session dev day-window control response data and behavior."""

    candidateSessionId: int
    candidateStatus: str
    status: Literal["ok", "dry_run"]
    targetDayIndex: int
    candidateTimezone: str
    scheduledStartAt: datetime
    scheduleLockedAt: datetime
    dayWindows: list[DayWindow]
    currentDayWindow: CurrentDayWindow | None = None
    auditId: str | None = None


class JobRequeueRequest(APIModel):
    """Represent job requeue request data and behavior."""

    reason: str = Field(..., min_length=3, max_length=500)
    force: bool = False


class JobRequeueResponse(APIModel):
    """Represent job requeue response data and behavior."""

    jobId: str
    previousStatus: str
    newStatus: str
    auditId: str


class TrialFallbackRequest(APIModel):
    """Represent trial fallback request data and behavior."""

    scenarioVersionId: int = Field(..., gt=0)
    applyTo: AdminApplyTo = "future_invites_only"
    reason: str = Field(..., min_length=3, max_length=500)
    dryRun: bool = False


class TrialFallbackResponse(APIModel):
    """Represent trial fallback response data and behavior."""

    trialId: int
    activeScenarioVersionId: int
    applyTo: AdminApplyTo
    auditId: str | None = None


class MediaRetentionPurgeRequest(APIModel):
    """Represent media retention purge request data and behavior."""

    retentionDays: int | None = Field(default=None, gt=0)
    batchLimit: int = Field(default=200, gt=0, le=1000)


class MediaRetentionPurgeResponse(APIModel):
    """Represent media retention purge response data and behavior."""

    status: Literal["ok"]
    scannedCount: int
    purgedCount: int
    failedCount: int
    purgedRecordingIds: list[int]


__all__ = [
    "AdminApplyTo",
    "AdminResetTargetState",
    "CandidateSessionDayWindowControlRequest",
    "CandidateSessionDayWindowControlResponse",
    "CandidateSessionResetRequest",
    "CandidateSessionResetResponse",
    "JobRequeueRequest",
    "JobRequeueResponse",
    "MediaRetentionPurgeRequest",
    "MediaRetentionPurgeResponse",
    "TrialFallbackRequest",
    "TrialFallbackResponse",
]
