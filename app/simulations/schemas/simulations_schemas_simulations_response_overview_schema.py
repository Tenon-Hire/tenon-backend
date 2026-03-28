"""Application module for simulations schemas simulations response overview schema workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.shared.types.shared_types_types_model import SimulationStatus
from app.simulations.schemas.simulations_schemas_simulations_ai_models_schema import (
    SimulationAIConfig,
    SimulationCompanyContext,
)
from app.simulations.schemas.simulations_schemas_simulations_scenario_summary_schema import (
    ScenarioVersionSummary,
)
from app.simulations.schemas.simulations_schemas_simulations_update_schema import (
    TaskOut,
)


class SimulationCreateResponse(BaseModel):
    """Response returned after creating a simulation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    role: str
    techStack: str
    seniority: str
    focus: str
    companyContext: SimulationCompanyContext | None = None
    ai: SimulationAIConfig | None = None
    templateKey: str
    status: SimulationStatus
    generatingAt: datetime | None = None
    readyForReviewAt: datetime | None = None
    activatedAt: datetime | None = None
    terminatedAt: datetime | None = None
    scenarioVersionSummary: ScenarioVersionSummary | None = None
    scenarioGenerationJobId: str
    tasks: list[TaskOut]


class SimulationListItem(BaseModel):
    """List item for recruiter dashboard simulations."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    role: str
    techStack: str
    seniority: str | None = None
    companyContext: SimulationCompanyContext | None = None
    ai: SimulationAIConfig | None = None
    templateKey: str
    status: SimulationStatus
    activatedAt: datetime | None = None
    terminatedAt: datetime | None = None
    scenarioVersionSummary: ScenarioVersionSummary | None = None
    createdAt: datetime
    numCandidates: int


__all__ = ["SimulationCreateResponse", "SimulationListItem"]
