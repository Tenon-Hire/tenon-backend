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
FitProfileCompareStatus = Literal["none", "generating", "ready", "failed"]


class SimulationCandidateCompareItem(APIModel):
    candidateSessionId: int
    candidateName: str
    candidateDisplayName: str
    status: CandidateCompareStatus
    fitProfileStatus: FitProfileCompareStatus
    overallFitScore: float | None = None
    recommendation: str | None = None
    dayCompletion: dict[str, bool] = Field(default_factory=dict)
    updatedAt: datetime


class SimulationCandidatesCompareResponse(APIModel):
    simulationId: int
    candidates: list[SimulationCandidateCompareItem] = Field(default_factory=list)


__all__ = [
    "CandidateCompareStatus",
    "FitProfileCompareStatus",
    "SimulationCandidateCompareItem",
    "SimulationCandidatesCompareResponse",
]
