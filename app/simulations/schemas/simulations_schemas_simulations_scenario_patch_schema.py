"""Application module for simulations schemas simulations scenario patch schema workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.simulations.schemas.simulations_schemas_simulations_limits_schema import (
    MAX_SCENARIO_NOTES_CHARS,
    MAX_SCENARIO_RUBRIC_BYTES,
    MAX_SCENARIO_STORYLINE_CHARS,
    MAX_SCENARIO_TASK_PROMPTS_BYTES,
    _json_payload_size_bytes,
)


def _compat_limit(name: str, default: int) -> int:
    # Keep limits monkeypatchable from the shared simulations schema module.
    from app.shared.types.schemas import (
        shared_types_schemas_simulations_schema as simulations_compat,
    )

    value = getattr(simulations_compat, name, default)
    return int(value)


class ScenarioVersionPatchTaskPrompt(BaseModel):
    """Full per-day prompt payload for scenario patching."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    dayIndex: int = Field(
        ..., ge=1, validation_alias=AliasChoices("dayIndex", "day_index")
    )
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=10_000)
    type: str | None = Field(default=None, min_length=1, max_length=100)


class ScenarioVersionPatchRequest(BaseModel):
    """Patch payload for an editable scenario version."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    storylineMd: str | None = Field(
        default=None, max_length=MAX_SCENARIO_STORYLINE_CHARS
    )
    taskPrompts: list[ScenarioVersionPatchTaskPrompt] | None = None
    rubric: dict[str, Any] | None = None
    notes: str | None = Field(default=None, max_length=MAX_SCENARIO_NOTES_CHARS)

    @field_validator("taskPrompts", mode="before")
    @classmethod
    def _validate_task_prompts_shape(cls, value: Any):
        if value is not None and not isinstance(value, list):
            raise ValueError("taskPrompts must be an array")
        return value

    @field_validator("taskPrompts")
    @classmethod
    def _validate_task_prompts_size(
        cls, value: list[ScenarioVersionPatchTaskPrompt] | None
    ):
        if value is None:
            return value
        serialized = [
            item.model_dump(by_alias=True, exclude_none=True) for item in value
        ]
        size_limit = _compat_limit(
            "MAX_SCENARIO_TASK_PROMPTS_BYTES",
            MAX_SCENARIO_TASK_PROMPTS_BYTES,
        )
        size_bytes = _json_payload_size_bytes(serialized)
        if size_bytes > size_limit:
            raise ValueError(f"taskPrompts exceeds {size_limit} bytes")
        return value

    @field_validator("rubric", mode="before")
    @classmethod
    def _validate_rubric_shape(cls, value: Any):
        if value is not None and not isinstance(value, Mapping):
            raise ValueError("rubric must be an object")
        return dict(value) if value is not None else value

    @field_validator("rubric")
    @classmethod
    def _validate_rubric_size(cls, value: dict[str, Any] | None):
        if value is None:
            return value
        size_limit = _compat_limit(
            "MAX_SCENARIO_RUBRIC_BYTES", MAX_SCENARIO_RUBRIC_BYTES
        )
        if _json_payload_size_bytes(value) > size_limit:
            raise ValueError(f"rubric exceeds {size_limit} bytes")
        return value

    @model_validator(mode="after")
    def _validate_non_empty_patch(self):
        editable_fields = {"storylineMd", "taskPrompts", "rubric", "notes"}
        if not self.model_fields_set.intersection(editable_fields):
            raise ValueError("At least one editable scenario field must be provided")
        return self


__all__ = ["ScenarioVersionPatchRequest", "ScenarioVersionPatchTaskPrompt"]
