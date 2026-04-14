"""Application module for trials schemas trials core schema workflows."""

from __future__ import annotations

from typing import Any

from app.tasks.schemas.tasks_schemas_tasks_public_schema import TaskPublic
from app.trials.schemas.trials_schemas_trials_ai_builders_schema import (
    build_trial_company_context,
)
from app.trials.schemas.trials_schemas_trials_ai_compat_schema import (
    build_trial_ai_config_with_resolver,
)
from app.trials.schemas.trials_schemas_trials_ai_models_schema import (
    TrialAIConfig,
    TrialCompanyContext,
    TrialDayWindowOverride,
)
from app.trials.schemas.trials_schemas_trials_ai_values_schema import (
    normalize_eval_enabled_by_day,
    resolve_trial_ai_fields,
)
from app.trials.schemas.trials_schemas_trials_create_schema import (
    TrialCreate,
)
from app.trials.schemas.trials_schemas_trials_exports_schema import (
    TRIALS_SCHEMA_EXPORTS,
)
from app.trials.schemas.trials_schemas_trials_limits_schema import (
    MAX_AI_NOTICE_TEXT_CHARS,
    MAX_AI_NOTICE_VERSION_CHARS,
    MAX_SCENARIO_NOTES_CHARS,
    MAX_SCENARIO_RUBRIC_BYTES,
    MAX_SCENARIO_STORYLINE_CHARS,
    MAX_SCENARIO_TASK_PROMPTS_BYTES,
    normalize_role_level,
)
from app.trials.schemas.trials_schemas_trials_response_detail_schema import (
    TrialDetailResponse,
    TrialDetailTask,
    TrialGenerationFailure,
    TrialLifecycleRequest,
)
from app.trials.schemas.trials_schemas_trials_response_overview_schema import (
    TrialCreateResponse,
    TrialListItem,
)
from app.trials.schemas.trials_schemas_trials_scenario_patch_schema import (
    ScenarioVersionPatchRequest,
    ScenarioVersionPatchTaskPrompt,
)
from app.trials.schemas.trials_schemas_trials_scenario_summary_schema import (
    ScenarioApproveResponse,
    ScenarioRegenerateResponse,
    ScenarioStateSummary,
    ScenarioVersionSummary,
    TrialDetailScenario,
)
from app.trials.schemas.trials_schemas_trials_scenario_update_schema import (
    ScenarioActiveUpdateRequest,
    ScenarioActiveUpdateResponse,
    ScenarioVersionPatchResponse,
    TrialActivateResponse,
    TrialTerminateResponse,
)
from app.trials.schemas.trials_schemas_trials_update_schema import (
    TaskOut,
    TrialUpdate,
)


def build_trial_ai_config(
    *,
    notice_version: str | None,
    notice_text: str | None,
    eval_enabled_by_day: Any,
    prompt_overrides_json: Any = None,
    prompt_pack_version: str | None = None,
    changes_pending_regeneration: bool | None = None,
    active_scenario_snapshot: Any = None,
    pending_scenario_snapshot: Any = None,
) -> TrialAIConfig | None:
    """Build trial ai config."""
    resolved = resolve_trial_ai_fields(
        notice_version=notice_version,
        notice_text=notice_text,
        eval_enabled_by_day=eval_enabled_by_day,
    )
    return build_trial_ai_config_with_resolver(
        notice_version=resolved[0],
        notice_text=resolved[1],
        eval_enabled_by_day=resolved[2],
        prompt_overrides_json=prompt_overrides_json,
        prompt_pack_version=prompt_pack_version,
        changes_pending_regeneration=changes_pending_regeneration,
        active_scenario_snapshot=active_scenario_snapshot,
        pending_scenario_snapshot=pending_scenario_snapshot,
        resolver=lambda **_kwargs: resolved,
    )


# Keep explicit references so Ruff understands these imports are intentional
# public re-exports from this compatibility schema module.
_TRIALS_SCHEMA_REEXPORTS = (
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
    TrialAIConfig,
    TrialActivateResponse,
    TrialCompanyContext,
    TrialCreate,
    TrialCreateResponse,
    TrialDayWindowOverride,
    TrialDetailResponse,
    TrialDetailScenario,
    TrialDetailTask,
    TrialGenerationFailure,
    TrialLifecycleRequest,
    TrialListItem,
    TrialTerminateResponse,
    TrialUpdate,
    TaskOut,
    TaskPublic,
    build_trial_company_context,
    normalize_eval_enabled_by_day,
    normalize_role_level,
    resolve_trial_ai_fields,
)


__all__ = TRIALS_SCHEMA_EXPORTS
