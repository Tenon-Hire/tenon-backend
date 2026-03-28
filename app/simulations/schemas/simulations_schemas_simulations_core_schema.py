"""Application module for simulations schemas simulations core schema workflows."""

from __future__ import annotations

from typing import Any

from app.simulations.schemas.simulations_schemas_simulations_ai_builders_schema import (
    build_simulation_company_context,
)
from app.simulations.schemas.simulations_schemas_simulations_ai_compat_schema import (
    build_simulation_ai_config_with_resolver,
)
from app.simulations.schemas.simulations_schemas_simulations_ai_models_schema import (
    SimulationAIConfig,
    SimulationCompanyContext,
    SimulationDayWindowOverride,
)
from app.simulations.schemas.simulations_schemas_simulations_ai_values_schema import (
    normalize_eval_enabled_by_day,
    resolve_simulation_ai_fields,
)
from app.simulations.schemas.simulations_schemas_simulations_create_schema import (
    SimulationCreate,
)
from app.simulations.schemas.simulations_schemas_simulations_exports_schema import (
    SIMULATIONS_SCHEMA_EXPORTS,
)
from app.simulations.schemas.simulations_schemas_simulations_limits_schema import (
    MAX_AI_NOTICE_TEXT_CHARS,
    MAX_AI_NOTICE_VERSION_CHARS,
    MAX_SCENARIO_NOTES_CHARS,
    MAX_SCENARIO_RUBRIC_BYTES,
    MAX_SCENARIO_STORYLINE_CHARS,
    MAX_SCENARIO_TASK_PROMPTS_BYTES,
    normalize_role_level,
)
from app.simulations.schemas.simulations_schemas_simulations_response_detail_schema import (
    SimulationDetailResponse,
    SimulationDetailTask,
    SimulationLifecycleRequest,
)
from app.simulations.schemas.simulations_schemas_simulations_response_overview_schema import (
    SimulationCreateResponse,
    SimulationListItem,
)
from app.simulations.schemas.simulations_schemas_simulations_scenario_patch_schema import (
    ScenarioVersionPatchRequest,
    ScenarioVersionPatchTaskPrompt,
)
from app.simulations.schemas.simulations_schemas_simulations_scenario_summary_schema import (
    ScenarioApproveResponse,
    ScenarioRegenerateResponse,
    ScenarioStateSummary,
    ScenarioVersionSummary,
    SimulationDetailScenario,
)
from app.simulations.schemas.simulations_schemas_simulations_scenario_update_schema import (
    ScenarioActiveUpdateRequest,
    ScenarioActiveUpdateResponse,
    ScenarioVersionPatchResponse,
    SimulationActivateResponse,
    SimulationTerminateResponse,
)
from app.simulations.schemas.simulations_schemas_simulations_update_schema import (
    SimulationUpdate,
    TaskOut,
)
from app.tasks.schemas.tasks_schemas_tasks_public_schema import TaskPublic


def build_simulation_ai_config(
    *,
    notice_version: str | None,
    notice_text: str | None,
    eval_enabled_by_day: Any,
) -> SimulationAIConfig | None:
    """Build simulation ai config."""
    return build_simulation_ai_config_with_resolver(
        notice_version=notice_version,
        notice_text=notice_text,
        eval_enabled_by_day=eval_enabled_by_day,
        resolver=resolve_simulation_ai_fields,
    )


# Keep explicit references so Ruff understands these imports are intentional
# public re-exports from this compatibility schema module.
_SIMULATIONS_SCHEMA_REEXPORTS = (
    ScenarioActiveUpdateRequest,
    ScenarioActiveUpdateResponse,
    ScenarioApproveResponse,
    ScenarioRegenerateResponse,
    ScenarioStateSummary,
    ScenarioVersionPatchRequest,
    ScenarioVersionPatchResponse,
    ScenarioVersionPatchTaskPrompt,
    ScenarioVersionSummary,
    MAX_AI_NOTICE_TEXT_CHARS,
    MAX_AI_NOTICE_VERSION_CHARS,
    MAX_SCENARIO_NOTES_CHARS,
    MAX_SCENARIO_RUBRIC_BYTES,
    MAX_SCENARIO_STORYLINE_CHARS,
    MAX_SCENARIO_TASK_PROMPTS_BYTES,
    SimulationAIConfig,
    SimulationActivateResponse,
    SimulationCompanyContext,
    SimulationCreate,
    SimulationCreateResponse,
    SimulationDayWindowOverride,
    SimulationDetailResponse,
    SimulationDetailScenario,
    SimulationDetailTask,
    SimulationLifecycleRequest,
    SimulationListItem,
    SimulationTerminateResponse,
    SimulationUpdate,
    TaskOut,
    TaskPublic,
    build_simulation_company_context,
    normalize_eval_enabled_by_day,
    normalize_role_level,
    resolve_simulation_ai_fields,
)


__all__ = SIMULATIONS_SCHEMA_EXPORTS
