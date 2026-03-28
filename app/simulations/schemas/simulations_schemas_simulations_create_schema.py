"""Application module for simulations schemas simulations create schema workflows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import time
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.config import settings
from app.simulations.schemas.simulations_schemas_simulations_ai_models_schema import (
    SimulationAIConfig,
    SimulationCompanyContext,
    SimulationDayWindowOverride,
)
from app.simulations.schemas.simulations_schemas_simulations_limits_schema import (
    _ALLOWED_DAY_WINDOW_OVERRIDE_KEYS,
    _ALLOWED_ROLE_LEVELS,
    MAX_FOCUS_NOTES_CHARS,
    normalize_role_level,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    DEFAULT_TEMPLATE_KEY,
    TemplateKeyError,
    validate_template_key,
)


class SimulationCreate(BaseModel):
    """Payload for creating a simulation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    title: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    techStack: str = Field(..., min_length=1, max_length=500)
    seniority: str = Field(
        ...,
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("seniority", "roleLevel", "role_level"),
    )
    focus: str = Field(
        ...,
        min_length=1,
        max_length=MAX_FOCUS_NOTES_CHARS,
        validation_alias=AliasChoices("focus", "focusNotes", "focus_notes"),
    )
    company_context: SimulationCompanyContext | None = Field(
        default=None, alias="companyContext"
    )
    ai: SimulationAIConfig | None = None
    templateKey: str = Field(
        DEFAULT_TEMPLATE_KEY, min_length=1, max_length=255, description="Template key"
    )
    dayWindowStartLocal: time = Field(default=time(hour=9, minute=0))
    dayWindowEndLocal: time = Field(default=time(hour=17, minute=0))
    dayWindowOverridesEnabled: bool = False
    dayWindowOverrides: dict[str, SimulationDayWindowOverride] | None = None

    @field_validator("seniority")
    @classmethod
    def _validate_seniority(cls, value: str) -> str:
        normalized = normalize_role_level(value)
        if normalized not in _ALLOWED_ROLE_LEVELS:
            allowed = ", ".join(sorted(_ALLOWED_ROLE_LEVELS))
            raise ValueError(f"seniority must be one of: {allowed}")
        return normalized

    @field_validator("templateKey")
    @classmethod
    def _validate_template_key(cls, value: str) -> str:
        try:
            return validate_template_key(value)
        except TemplateKeyError as exc:
            raise ValueError(str(exc)) from None

    @field_validator("dayWindowOverrides", mode="before")
    @classmethod
    def _validate_day_window_overrides(cls, value: Any):
        if value is None:
            return None
        if not settings.SCHEDULE_DAY_WINDOW_OVERRIDES_ENABLED:
            raise ValueError("dayWindowOverrides is disabled")
        if not isinstance(value, Mapping):
            raise ValueError("dayWindowOverrides must be an object")
        normalized: dict[str, Any] = {}
        for raw_key, raw_val in value.items():
            day_key = str(raw_key).strip()
            if day_key not in _ALLOWED_DAY_WINDOW_OVERRIDE_KEYS:
                allowed = ", ".join(sorted(_ALLOWED_DAY_WINDOW_OVERRIDE_KEYS))
                raise ValueError(f"dayWindowOverrides keys must be one of: {allowed}")
            normalized[day_key] = raw_val
        return normalized

    @model_validator(mode="after")
    def _validate_day_window_bounds(self):
        if self.dayWindowEndLocal <= self.dayWindowStartLocal:
            raise ValueError("dayWindowEndLocal must be after dayWindowStartLocal")
        if self.dayWindowOverrides and not self.dayWindowOverridesEnabled:
            raise ValueError(
                "dayWindowOverridesEnabled must be true when dayWindowOverrides is set"
            )
        return self


__all__ = ["SimulationCreate"]
