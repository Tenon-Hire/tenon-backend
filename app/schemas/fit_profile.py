from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.domains.common.base import APIModel


class FitProfileGenerateResponse(APIModel):
    jobId: str
    status: Literal["queued"]


class FitProfileEvidenceOut(APIModel):
    kind: str
    ref: str | None = None
    url: str | None = None
    excerpt: str | None = None
    startMs: int | None = None
    endMs: int | None = None


class FitProfileDayScoreOut(APIModel):
    dayIndex: int
    score: float | None = None
    rubricBreakdown: dict[str, Any] = Field(default_factory=dict)
    evidence: list[FitProfileEvidenceOut] = Field(default_factory=list)
    status: str | None = None
    reason: str | None = None


class FitProfileVersionOut(APIModel):
    model: str
    promptVersion: str
    rubricVersion: str
    modelVersion: str | None = None


class FitProfileReportOut(APIModel):
    overallFitScore: float
    recommendation: str
    confidence: float
    dayScores: list[FitProfileDayScoreOut] = Field(default_factory=list)
    version: FitProfileVersionOut
    disabledDayIndexes: list[int] | None = None


class FitProfileStatusResponse(APIModel):
    status: Literal["not_started", "running", "ready", "failed"]
    generatedAt: datetime | None = None
    report: FitProfileReportOut | None = None
    errorCode: str | None = None


__all__ = [
    "FitProfileDayScoreOut",
    "FitProfileEvidenceOut",
    "FitProfileGenerateResponse",
    "FitProfileReportOut",
    "FitProfileStatusResponse",
    "FitProfileVersionOut",
]
