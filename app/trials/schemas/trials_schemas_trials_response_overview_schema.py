"""Application module for trials schemas trials response overview schema workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.shared.types.shared_types_types_model import TrialStatus
from app.trials.schemas.trials_schemas_trials_ai_models_schema import (
    TrialAIConfig,
    TrialCompanyContext,
)
from app.trials.schemas.trials_schemas_trials_update_schema import (
    TaskOut,
)


class TrialCreateResponse(BaseModel):
    """Response returned after creating a trial."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    role: str
    seniority: str
    focus: str
    companyContext: TrialCompanyContext | None = None
    ai: TrialAIConfig | None = None
    status: TrialStatus
    generatingAt: datetime | None = None
    readyForReviewAt: datetime | None = None
    activatedAt: datetime | None = None
    terminatedAt: datetime | None = None
    scenarioGenerationJobId: str
    tasks: list[TaskOut]


class TrialListItem(BaseModel):
    """List item for Talent Partner dashboard trials."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    role: str
    seniority: str | None = None
    companyContext: TrialCompanyContext | None = None
    ai: TrialAIConfig | None = None
    status: TrialStatus
    activatedAt: datetime | None = None
    terminatedAt: datetime | None = None
    createdAt: datetime
    numCandidates: int


__all__ = ["TrialCreateResponse", "TrialListItem"]
