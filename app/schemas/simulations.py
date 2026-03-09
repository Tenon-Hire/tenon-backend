from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, time
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    ValidationError,
    field_validator,
    model_serializer,
    model_validator,
)

from app.core.settings import settings
from app.domains.common.types import SimulationStatus, TaskType
from app.domains.tasks.schemas_public import TaskPublic
from app.services.tasks.template_catalog import (
    DEFAULT_TEMPLATE_KEY,
    TemplateKeyError,
    validate_template_key,
)

__all__ = [
    "SimulationCreate",
    "TaskOut",
    "SimulationCreateResponse",
    "SimulationListItem",
    "SimulationDetailResponse",
    "SimulationDetailTask",
    "SimulationDetailScenario",
    "SimulationLifecycleRequest",
    "SimulationActivateResponse",
    "SimulationTerminateResponse",
    "ScenarioVersionSummary",
    "ScenarioStateSummary",
    "ScenarioRegenerateResponse",
    "ScenarioActiveUpdateRequest",
    "ScenarioActiveUpdateResponse",
    "SimulationCompanyContext",
    "SimulationAIConfig",
    "SimulationDayWindowOverride",
    "normalize_role_level",
    "normalize_eval_enabled_by_day",
    "build_simulation_ai_config",
    "build_simulation_company_context",
    "TaskPublic",
]

MAX_FOCUS_NOTES_CHARS = 1000
MAX_COMPANY_CONTEXT_VALUE_CHARS = 120
MAX_AI_NOTICE_VERSION_CHARS = 100
MAX_AI_NOTICE_TEXT_CHARS = 2000
_ALLOWED_ROLE_LEVELS = frozenset({"junior", "mid", "senior", "staff", "principal"})
_ALLOWED_AI_EVAL_DAY_KEYS = frozenset({"1", "2", "3", "4", "5"})
_ALLOWED_DAY_WINDOW_OVERRIDE_KEYS = frozenset(str(day) for day in range(9, 22))


def normalize_role_level(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized if normalized in _ALLOWED_ROLE_LEVELS else None


def normalize_eval_enabled_by_day(
    value: Any, *, strict: bool
) -> dict[str, bool] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        if strict:
            raise ValueError("evalEnabledByDay must be an object mapping day to bool")
        return None

    normalized: dict[str, bool] = {}
    for raw_key, raw_value in value.items():
        day_key = str(raw_key).strip()
        if day_key not in _ALLOWED_AI_EVAL_DAY_KEYS:
            if strict:
                allowed = ", ".join(sorted(_ALLOWED_AI_EVAL_DAY_KEYS))
                raise ValueError(f"evalEnabledByDay day keys must be one of: {allowed}")
            continue
        if not isinstance(raw_value, bool):
            if strict:
                raise ValueError(
                    f"evalEnabledByDay[{day_key}] must be a boolean true/false value"
                )
            continue
        normalized[day_key] = raw_value
    return normalized


class SimulationCompanyContext(BaseModel):
    """Allowlisted company context passed to scenario generation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    domain: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_COMPANY_CONTEXT_VALUE_CHARS,
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
        default=None,
        alias="evalEnabledByDay",
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


def build_simulation_company_context(
    value: Any,
) -> SimulationCompanyContext | None:
    if not isinstance(value, Mapping):
        return None
    try:
        return SimulationCompanyContext.model_validate(dict(value))
    except ValidationError:
        return None


def build_simulation_ai_config(
    *,
    notice_version: str | None,
    notice_text: str | None,
    eval_enabled_by_day: Any,
) -> SimulationAIConfig | None:
    normalized_eval = normalize_eval_enabled_by_day(eval_enabled_by_day, strict=False)
    if notice_version is None and notice_text is None and normalized_eval is None:
        return None

    payload: dict[str, Any] = {}
    if notice_version is not None:
        payload["noticeVersion"] = notice_version
    if notice_text is not None:
        payload["noticeText"] = notice_text
    if normalized_eval is not None:
        payload["evalEnabledByDay"] = normalized_eval
    try:
        return SimulationAIConfig.model_validate(payload)
    except ValidationError:
        return None


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
        default=None,
        alias="companyContext",
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


class TaskOut(BaseModel):
    """Response model for a created task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    day_index: int
    type: TaskType
    title: str = Field(..., min_length=1, max_length=200)


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
    modelName: str | None = None
    modelVersion: str | None = None
    promptVersion: str | None = None
    rubricVersion: str | None = None


class ScenarioRegenerateResponse(BaseModel):
    """Response for scenario regeneration."""

    simulationId: int
    scenario: ScenarioStateSummary


class ScenarioActiveUpdateRequest(BaseModel):
    """Minimal payload to mutate the active scenario version."""

    storylineMd: str | None = None
    taskPromptsJson: dict | list | None = None
    rubricJson: dict | list | None = None
    focusNotes: str | None = None
    status: str | None = None


class ScenarioActiveUpdateResponse(BaseModel):
    """Response for active scenario version mutation."""

    simulationId: int
    scenario: ScenarioStateSummary


class SimulationCreateResponse(BaseModel):
    """Response returned after creating a simulation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    role: str
    techStack: str
    seniority: str
    focus: str
    companyContext: SimulationCompanyContext | None = None
    ai: SimulationAIConfig | None = None
    templateKey: str
    status: SimulationStatus
    generatingAt: datetime | None = None
    readyForReviewAt: datetime | None = None
    activatedAt: datetime | None = None
    terminatedAt: datetime | None = None
    scenarioVersionSummary: ScenarioVersionSummary | None = None
    scenarioGenerationJobId: str
    tasks: list[TaskOut]


class SimulationListItem(BaseModel):
    """List item for recruiter dashboard simulations."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    role: str
    techStack: str
    seniority: str | None = None
    companyContext: SimulationCompanyContext | None = None
    ai: SimulationAIConfig | None = None
    templateKey: str
    status: SimulationStatus
    activatedAt: datetime | None = None
    terminatedAt: datetime | None = None
    scenarioVersionSummary: ScenarioVersionSummary | None = None
    createdAt: datetime
    numCandidates: int


class SimulationDetailTask(BaseModel):
    """Task summary for recruiter simulation detail view."""

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


class SimulationDetailResponse(BaseModel):
    """Detail view response for a simulation (recruiter-only)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None = None
    templateKey: str | None = None
    role: str | None = None
    seniority: str | None = None
    techStack: str | list[str] | None = None
    focus: str | list[str] | None = None
    companyContext: SimulationCompanyContext | None = None
    ai: SimulationAIConfig | None = None
    scenario: SimulationDetailScenario | None = None
    status: SimulationStatus
    generatingAt: datetime | None = None
    readyForReviewAt: datetime | None = None
    activatedAt: datetime | None = None
    terminatedAt: datetime | None = None
    scenarioVersionSummary: ScenarioVersionSummary | None = None
    tasks: list[SimulationDetailTask]


class SimulationLifecycleRequest(BaseModel):
    """Confirmation payload for lifecycle transitions."""

    confirm: bool
    reason: str | None = Field(default=None, min_length=1, max_length=500)


class SimulationActivateResponse(BaseModel):
    """Response payload for simulation activation."""

    simulationId: int
    status: SimulationStatus
    activatedAt: datetime | None = None


class SimulationTerminateResponse(BaseModel):
    """Response payload for simulation termination."""

    simulationId: int
    status: SimulationStatus
    terminatedAt: datetime | None = None
    cleanupJobIds: list[str] = Field(default_factory=list)
