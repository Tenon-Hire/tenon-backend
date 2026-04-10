"""Application module for trials schemas trials response detail schema workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_serializer

from app.shared.types.shared_types_types_model import TaskType, TrialStatus
from app.trials.schemas.trials_schemas_trials_ai_models_schema import (
    TrialAIConfig,
    TrialCompanyContext,
)
from app.trials.schemas.trials_schemas_trials_scenario_summary_schema import (
    ScenarioVersionSummary,
    TrialDetailScenario,
)


class TrialDetailTask(BaseModel):
    """Task summary for Talent Partner trial detail view."""

    model_config = ConfigDict(from_attributes=True)

    dayIndex: int
    title: str | None = None
    type: TaskType | None = None
    description: str | None = None
    rubric: str | list[str] | dict | None = None
    maxScore: int | None = None
    preProvisioned: bool | None = None
    templateRepoFullName: str | None = None

    @model_serializer(mode="plain")
    def _serialize(self):
        data = {
            "dayIndex": self.dayIndex,
            "title": self.title,
            "type": self.type,
            "description": self.description,
            "rubric": self.rubric,
        }
        if self.maxScore is not None:
            data["maxScore"] = self.maxScore
        if self.preProvisioned is not None:
            data["preProvisioned"] = self.preProvisioned
        if self.templateRepoFullName is not None:
            data["templateRepoFullName"] = self.templateRepoFullName
        return data


class TrialDetailResponse(BaseModel):
    """Detail view response for a trial (Talent Partner-only)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None = None
    templateKey: str | None = None
    role: str | None = None
    seniority: str | None = None
    techStack: str | list[str] | None = None
    focus: str | list[str] | None = None
    companyContext: TrialCompanyContext | None = None
    ai: TrialAIConfig | None = None
    activeScenarioVersionId: int | None = None
    pendingScenarioVersionId: int | None = None
    scenario: TrialDetailScenario | None = None
    status: TrialStatus
    generatingAt: datetime | None = None
    readyForReviewAt: datetime | None = None
    activatedAt: datetime | None = None
    terminatedAt: datetime | None = None
    scenarioVersionSummary: ScenarioVersionSummary | None = None
    tasks: list[TrialDetailTask]


class TrialLifecycleRequest(BaseModel):
    """Confirmation payload for lifecycle transitions."""

    confirm: bool
    reason: str | None = Field(default=None, min_length=1, max_length=500)


__all__ = [
    "TrialDetailResponse",
    "TrialDetailTask",
    "TrialLifecycleRequest",
]
