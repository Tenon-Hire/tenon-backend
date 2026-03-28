"""Application module for evaluations schemas evaluations fit profile schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.shared.types.shared_types_base_model import APIModel


class FitProfileGenerateResponse(APIModel):
    """Represent fit profile generate response data and behavior."""

    jobId: str
    status: Literal["queued"]


class FitProfileEvidenceOut(APIModel):
    """Represent fit profile evidence out data and behavior."""

    kind: str
    ref: str | None = None
    url: str | None = None
    excerpt: str | None = None
    startMs: int | None = None
    endMs: int | None = None


class FitProfileDayScoreOut(APIModel):
    """Represent fit profile day score out data and behavior."""

    dayIndex: int
    score: float | None = None
    rubricBreakdown: dict[str, Any] = Field(default_factory=dict)
    evidence: list[FitProfileEvidenceOut] = Field(default_factory=list)
    status: str | None = None
    reason: str | None = None


class FitProfileVersionOut(APIModel):
    """Represent fit profile version out data and behavior."""

    model: str
    promptVersion: str
    rubricVersion: str
    modelVersion: str | None = None


class FitProfileReportOut(APIModel):
    """Represent fit profile report out data and behavior."""

    overallFitScore: float
    recommendation: str
    confidence: float
    dayScores: list[FitProfileDayScoreOut] = Field(default_factory=list)
    version: FitProfileVersionOut
    disabledDayIndexes: list[int] | None = None


class FitProfileStatusResponse(APIModel):
    """Represent fit profile status response data and behavior."""

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
