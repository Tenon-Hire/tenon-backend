"""Application module for simulations schemas simulations scenario update schema workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.types.shared_types_types_model import SimulationStatus
from app.simulations.schemas.simulations_schemas_simulations_scenario_summary_schema import (
    ScenarioStateSummary,
)


class ScenarioVersionPatchResponse(BaseModel):
    """Response for scenario version patch requests."""

    scenarioVersionId: int
    status: str


class ScenarioActiveUpdateRequest(BaseModel):
    """Minimal payload to mutate the active scenario version."""

    storylineMd: str | None = None
    taskPromptsJson: dict | list | None = None
    rubricJson: dict | list | None = None
    focusNotes: str | None = None
    status: str | None = None


class ScenarioActiveUpdateResponse(BaseModel):
    """Response for active scenario version mutation."""

    simulationId: int
    scenario: ScenarioStateSummary


class SimulationActivateResponse(BaseModel):
    """Response payload for simulation activation."""

    simulationId: int
    status: SimulationStatus
    activatedAt: datetime | None = None


class SimulationTerminateResponse(BaseModel):
    """Response payload for simulation termination."""

    simulationId: int
    status: SimulationStatus
    terminatedAt: datetime | None = None
    cleanupJobIds: list[str] = Field(default_factory=list)


__all__ = [
    "ScenarioActiveUpdateRequest",
    "ScenarioActiveUpdateResponse",
    "ScenarioVersionPatchResponse",
    "SimulationActivateResponse",
    "SimulationTerminateResponse",
]
