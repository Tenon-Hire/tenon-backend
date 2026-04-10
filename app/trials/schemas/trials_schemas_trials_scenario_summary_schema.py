"""Application module for trials schemas trials scenario summary schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.shared.types.shared_types_types_model import TrialStatus
from app.trials.schemas.trials_schemas_trials_ai_models_schema import (
    TrialAIAgentRuntimeSummary,
)


class ScenarioVersionSummary(BaseModel):
    """Stable summary for scenario/version related metadata."""

    templateKey: str | None = None
    scenarioTemplate: str | None = None


class ScenarioStateSummary(BaseModel):
    """Scenario version metadata shown on trial detail."""

    id: int
    versionIndex: int
    status: str
    lockedAt: datetime | None = None


class TrialDetailScenario(ScenarioStateSummary):
    """Expanded scenario payload for trial detail views."""

    storylineMd: str | None = None
    taskPromptsJson: list[dict[str, Any]] | dict[str, Any] | list[Any] | None = None
    rubricJson: dict[str, Any] | list[Any] | None = None
    notes: str | None = None
    modelName: str | None = None
    modelVersion: str | None = None
    promptVersion: str | None = None
    rubricVersion: str | None = None
    aiPolicySnapshotDigest: str | None = None
    aiPromptPackVersion: str | None = None
    precommitBundleStatus: str | None = None
    agentRuntimeSummary: list[TrialAIAgentRuntimeSummary] | None = None


class ScenarioRegenerateResponse(BaseModel):
    """Response for scenario regeneration."""

    scenarioVersionId: int
    jobId: str
    status: str


class ScenarioApproveResponse(BaseModel):
    """Response for explicit scenario version approval."""

    trialId: int
    status: TrialStatus
    activeScenarioVersionId: int
    pendingScenarioVersionId: int | None = None
    scenario: ScenarioStateSummary


__all__ = [
    "ScenarioApproveResponse",
    "ScenarioRegenerateResponse",
    "ScenarioStateSummary",
    "ScenarioVersionSummary",
    "TrialDetailScenario",
]
