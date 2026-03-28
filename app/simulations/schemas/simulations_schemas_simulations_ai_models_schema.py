"""Application module for simulations schemas simulations ai models schema workflows."""

from __future__ import annotations

from datetime import time
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_serializer,
    model_validator,
)

from app.simulations.schemas.simulations_schemas_simulations_ai_values_schema import (
    normalize_eval_enabled_by_day,
)
from app.simulations.schemas.simulations_schemas_simulations_limits_schema import (
    MAX_AI_NOTICE_TEXT_CHARS,
    MAX_AI_NOTICE_VERSION_CHARS,
    MAX_COMPANY_CONTEXT_VALUE_CHARS,
)


class SimulationCompanyContext(BaseModel):
    """Allowlisted company context passed to scenario generation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    domain: str | None = Field(
        default=None, min_length=1, max_length=MAX_COMPANY_CONTEXT_VALUE_CHARS
    )
    product_area: str | None = Field(
        default=None,
        alias="productArea",
        min_length=1,
        max_length=MAX_COMPANY_CONTEXT_VALUE_CHARS,
    )

    @model_serializer(mode="plain")
    def _serialize(self):
        data: dict[str, Any] = {}
        if self.domain is not None:
            data["domain"] = self.domain
        if self.product_area is not None:
            data["productArea"] = self.product_area
        return data


class SimulationAIConfig(BaseModel):
    """AI notice/toggle controls for a simulation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    notice_version: str | None = Field(
        default=None,
        alias="noticeVersion",
        min_length=1,
        max_length=MAX_AI_NOTICE_VERSION_CHARS,
    )
    notice_text: str | None = Field(
        default=None,
        alias="noticeText",
        min_length=1,
        max_length=MAX_AI_NOTICE_TEXT_CHARS,
    )
    eval_enabled_by_day: dict[str, StrictBool] | None = Field(
        default=None, alias="evalEnabledByDay"
    )

    @field_validator("eval_enabled_by_day", mode="before")
    @classmethod
    def _validate_eval_enabled_by_day(cls, value: Any):
        return normalize_eval_enabled_by_day(value, strict=True)

    @model_serializer(mode="plain")
    def _serialize(self):
        data: dict[str, Any] = {}
        if self.notice_version is not None:
            data["noticeVersion"] = self.notice_version
        if self.notice_text is not None:
            data["noticeText"] = self.notice_text
        if self.eval_enabled_by_day is not None:
            data["evalEnabledByDay"] = self.eval_enabled_by_day
        return data


class SimulationDayWindowOverride(BaseModel):
    """Optional per-day local schedule window override."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    start_local: time = Field(alias="startLocal")
    end_local: time = Field(alias="endLocal")

    @model_validator(mode="after")
    def _validate_bounds(self):
        if self.end_local <= self.start_local:
            raise ValueError("endLocal must be after startLocal")
        return self

    @model_serializer(mode="plain")
    def _serialize(self):
        return {
            "startLocal": self.start_local.strftime("%H:%M"),
            "endLocal": self.end_local.strftime("%H:%M"),
        }


__all__ = [
    "SimulationAIConfig",
    "SimulationCompanyContext",
    "SimulationDayWindowOverride",
]
