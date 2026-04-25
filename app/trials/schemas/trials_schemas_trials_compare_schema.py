"""Application module for trials schemas trials compare schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.shared.types.shared_types_base_model import APIModel

CandidateCompareStatus = Literal[
    "scheduled",
    "in_progress",
    "completed",
    "evaluated",
]
WinoeReportCompareStatus = Literal["none", "generating", "ready", "failed"]
PublicCompareRecommendation = Literal[
    "strong_signal",
    "positive_signal",
    "mixed_signal",
    "limited_signal",
]


class TrialCandidateCompareItem(APIModel):
    """Represent trial candidate compare item data and behavior."""

    candidateSessionId: int
    candidateName: str
    candidateDisplayName: str
    status: CandidateCompareStatus
    winoeReportStatus: WinoeReportCompareStatus
    overallWinoeScore: float | None = None
    recommendation: PublicCompareRecommendation | None = None
    dayCompletion: dict[str, bool] = Field(default_factory=dict)
    updatedAt: datetime


class TrialCandidatesCompareResponse(APIModel):
    """Represent trial candidates compare response data and behavior."""

    trialId: int
    cohortSize: int = 0
    state: Literal["empty", "partial", "ready"] = "empty"
    message: str | None = None
    candidates: list[TrialCandidateCompareItem] = Field(default_factory=list)


__all__ = [
    "CandidateCompareStatus",
    "PublicCompareRecommendation",
    "WinoeReportCompareStatus",
    "TrialCandidateCompareItem",
    "TrialCandidatesCompareResponse",
]
