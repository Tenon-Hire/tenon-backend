"""Application module for evaluations schemas evaluations winoe report schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.shared.types.shared_types_base_model import APIModel


class WinoeReportGenerateResponse(APIModel):
    """Represent winoe report generate response data and behavior."""

    jobId: str
    status: Literal["queued"]


class WinoeReportEvidenceOut(APIModel):
    """Represent winoe report evidence out data and behavior."""

    kind: str
    ref: str | None = None
    url: str | None = None
    excerpt: str | None = None
    startMs: int | None = None
    endMs: int | None = None


class WinoeReportDayScoreOut(APIModel):
    """Represent winoe report day score out data and behavior."""

    dayIndex: int
    score: float | None = None
    rubricBreakdown: dict[str, Any] = Field(default_factory=dict)
    evidence: list[WinoeReportEvidenceOut] = Field(default_factory=list)
    status: str | None = None
    reason: str | None = None


class WinoeReportVersionOut(APIModel):
    """Represent winoe report version out data and behavior."""

    model: str
    promptVersion: str
    rubricVersion: str
    modelVersion: str | None = None


class WinoeReportReportOut(APIModel):
    """Represent winoe report report out data and behavior."""

    overallWinoeScore: float
    recommendation: Literal[
        "strong_signal",
        "positive_signal",
        "mixed_signal",
        "limited_signal",
    ]
    confidence: float
    dayScores: list[WinoeReportDayScoreOut] = Field(default_factory=list)
    version: WinoeReportVersionOut
    disabledDayIndexes: list[int] | None = None


class WinoeReportStatusResponse(APIModel):
    """Represent winoe report status response data and behavior."""

    status: Literal["not_started", "running", "ready", "failed"]
    generatedAt: datetime | None = None
    report: WinoeReportReportOut | None = None
    errorCode: str | None = None


__all__ = [
    "WinoeReportDayScoreOut",
    "WinoeReportEvidenceOut",
    "WinoeReportGenerateResponse",
    "WinoeReportReportOut",
    "WinoeReportStatusResponse",
    "WinoeReportVersionOut",
]
