from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domains.common.base import APIModel

AdminResetTargetState = Literal["not_started", "claimed", "in_progress"]
AdminApplyTo = Literal["future_invites_only"]


class CandidateSessionResetRequest(APIModel):
    targetState: AdminResetTargetState
    reason: str = Field(..., min_length=3, max_length=500)
    overrideIfEvaluated: bool = False
    dryRun: bool = False


class CandidateSessionResetResponse(APIModel):
    candidateSessionId: int
    status: Literal["ok", "dry_run"]
    resetTo: AdminResetTargetState
    auditId: str | None = None


class JobRequeueRequest(APIModel):
    reason: str = Field(..., min_length=3, max_length=500)
    force: bool = False


class JobRequeueResponse(APIModel):
    jobId: str
    previousStatus: str
    newStatus: str
    auditId: str


class SimulationFallbackRequest(APIModel):
    scenarioVersionId: int = Field(..., gt=0)
    applyTo: AdminApplyTo = "future_invites_only"
    reason: str = Field(..., min_length=3, max_length=500)
    dryRun: bool = False


class SimulationFallbackResponse(APIModel):
    simulationId: int
    activeScenarioVersionId: int
    applyTo: AdminApplyTo
    auditId: str | None = None


class MediaRetentionPurgeRequest(APIModel):
    retentionDays: int | None = Field(default=None, gt=0)
    batchLimit: int = Field(default=200, gt=0, le=1000)


class MediaRetentionPurgeResponse(APIModel):
    status: Literal["ok"]
    scannedCount: int
    purgedCount: int
    failedCount: int
    purgedRecordingIds: list[int]


__all__ = [
    "AdminApplyTo",
    "AdminResetTargetState",
    "CandidateSessionResetRequest",
    "CandidateSessionResetResponse",
    "JobRequeueRequest",
    "JobRequeueResponse",
    "MediaRetentionPurgeRequest",
    "MediaRetentionPurgeResponse",
    "SimulationFallbackRequest",
    "SimulationFallbackResponse",
]
