"""Application module for simulations schemas simulations compare schema workflows."""

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
    """Represent simulation candidate compare item data and behavior."""

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
    """Represent simulation candidates compare response data and behavior."""

    simulationId: int
    candidates: list[SimulationCandidateCompareItem] = Field(default_factory=list)


__all__ = [
    "CandidateCompareStatus",
    "FitProfileCompareStatus",
    "SimulationCandidateCompareItem",
    "SimulationCandidatesCompareResponse",
]
