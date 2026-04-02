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

from app.ai import PromptOverrideSet
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


class SimulationAIAgentRuntimeSummary(BaseModel):
    """Recruiter-visible summary of one frozen agent policy/runtime."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    key: str
    provider: str | None = None
    model: str | None = None
    runtime_mode: str | None = Field(default=None, alias="runtimeMode")
    prompt_version: str | None = Field(default=None, alias="promptVersion")
    rubric_version: str | None = Field(default=None, alias="rubricVersion")

    @model_serializer(mode="plain")
    def _serialize(self):
        data: dict[str, Any] = {"key": self.key}
        if self.provider is not None:
            data["provider"] = self.provider
        if self.model is not None:
            data["model"] = self.model
        if self.runtime_mode is not None:
            data["runtimeMode"] = self.runtime_mode
        if self.prompt_version is not None:
            data["promptVersion"] = self.prompt_version
        if self.rubric_version is not None:
            data["rubricVersion"] = self.rubric_version
        return data


class SimulationAISnapshotSummary(BaseModel):
    """Frozen AI snapshot summary for one scenario version."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    scenario_version_id: int = Field(alias="scenarioVersionId")
    snapshot_digest: str | None = Field(default=None, alias="snapshotDigest")
    prompt_pack_version: str | None = Field(default=None, alias="promptPackVersion")
    bundle_status: str | None = Field(default=None, alias="bundleStatus")
    agents: list[SimulationAIAgentRuntimeSummary] | None = None

    @model_serializer(mode="plain")
    def _serialize(self):
        data: dict[str, Any] = {"scenarioVersionId": self.scenario_version_id}
        if self.snapshot_digest is not None:
            data["snapshotDigest"] = self.snapshot_digest
        if self.prompt_pack_version is not None:
            data["promptPackVersion"] = self.prompt_pack_version
        if self.bundle_status is not None:
            data["bundleStatus"] = self.bundle_status
        if self.agents is not None:
            data["agents"] = [
                agent.model_dump(by_alias=True, exclude_none=True)
                for agent in self.agents
            ]
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
    prompt_overrides: PromptOverrideSet | None = Field(
        default=None,
        alias="promptOverrides",
    )
    prompt_pack_version: str | None = Field(
        default=None,
        alias="promptPackVersion",
        min_length=1,
        max_length=255,
    )
    changes_pending_regeneration: bool | None = Field(
        default=None,
        alias="changesPendingRegeneration",
    )
    active_scenario_snapshot: SimulationAISnapshotSummary | None = Field(
        default=None,
        alias="activeScenarioSnapshot",
    )
    pending_scenario_snapshot: SimulationAISnapshotSummary | None = Field(
        default=None,
        alias="pendingScenarioSnapshot",
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
        if self.prompt_overrides is not None:
            data["promptOverrides"] = self.prompt_overrides.model_dump(
                by_alias=True,
                exclude_none=True,
            )
        if self.prompt_pack_version is not None:
            data["promptPackVersion"] = self.prompt_pack_version
        if self.changes_pending_regeneration is not None:
            data["changesPendingRegeneration"] = self.changes_pending_regeneration
        if self.active_scenario_snapshot is not None:
            data["activeScenarioSnapshot"] = self.active_scenario_snapshot.model_dump(
                by_alias=True,
                exclude_none=True,
            )
        if self.pending_scenario_snapshot is not None:
            data["pendingScenarioSnapshot"] = self.pending_scenario_snapshot.model_dump(
                by_alias=True,
                exclude_none=True,
            )
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
    "SimulationAIAgentRuntimeSummary",
    "SimulationAISnapshotSummary",
    "SimulationCompanyContext",
    "SimulationDayWindowOverride",
]
