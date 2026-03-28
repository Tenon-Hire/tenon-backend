"""Application module for simulations schemas simulations scenario summary schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.shared.types.shared_types_types_model import SimulationStatus


class ScenarioVersionSummary(BaseModel):
    """Stable summary for scenario/version related metadata."""

    templateKey: str | None = None
    scenarioTemplate: str | None = None


class ScenarioStateSummary(BaseModel):
    """Scenario version metadata shown on simulation detail."""

    id: int
    versionIndex: int
    status: str
    lockedAt: datetime | None = None


class SimulationDetailScenario(ScenarioStateSummary):
    """Expanded scenario payload for simulation detail views."""

    storylineMd: str | None = None
    taskPromptsJson: list[dict[str, Any]] | dict[str, Any] | list[Any] | None = None
    rubricJson: dict[str, Any] | list[Any] | None = None
    notes: str | None = None
    modelName: str | None = None
    modelVersion: str | None = None
    promptVersion: str | None = None
    rubricVersion: str | None = None


class ScenarioRegenerateResponse(BaseModel):
    """Response for scenario regeneration."""

    scenarioVersionId: int
    jobId: str
    status: str


class ScenarioApproveResponse(BaseModel):
    """Response for explicit scenario version approval."""

    simulationId: int
    status: SimulationStatus
    activeScenarioVersionId: int
    pendingScenarioVersionId: int | None = None
    scenario: ScenarioStateSummary


__all__ = [
    "ScenarioApproveResponse",
    "ScenarioRegenerateResponse",
    "ScenarioStateSummary",
    "ScenarioVersionSummary",
    "SimulationDetailScenario",
]
