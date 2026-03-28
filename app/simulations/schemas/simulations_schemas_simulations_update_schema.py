"""Application module for simulations schemas simulations update schema workflows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.shared.types.shared_types_types_model import TaskType
from app.simulations.schemas.simulations_schemas_simulations_ai_models_schema import (
    SimulationAIConfig,
)


class SimulationUpdate(BaseModel):
    """Payload for updating mutable simulation configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    ai: SimulationAIConfig | None = None


class TaskOut(BaseModel):
    """Response model for a created task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    day_index: int
    type: TaskType
    title: str = Field(..., min_length=1, max_length=200)


__all__ = ["SimulationUpdate", "TaskOut"]
