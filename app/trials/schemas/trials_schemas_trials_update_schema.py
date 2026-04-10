"""Application module for trials schemas trials update schema workflows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.shared.types.shared_types_types_model import TaskType
from app.trials.schemas.trials_schemas_trials_ai_models_schema import (
    TrialAIConfig,
)


class TrialUpdate(BaseModel):
    """Payload for updating mutable trial configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    ai: TrialAIConfig | None = None


class TaskOut(BaseModel):
    """Response model for a created task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    day_index: int
    type: TaskType
    title: str = Field(..., min_length=1, max_length=200)


__all__ = ["TrialUpdate", "TaskOut"]
