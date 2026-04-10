"""Application module for trials schemas trials ai builders schema workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.ai import normalize_prompt_override_payload
from app.trials.constants.trials_constants_trials_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.trials.schemas.trials_schemas_trials_ai_models_schema import (
    TrialAIConfig,
    TrialCompanyContext,
)
from app.trials.schemas.trials_schemas_trials_ai_values_schema import (
    resolve_trial_ai_fields,
)


def build_trial_company_context(value: Any) -> TrialCompanyContext | None:
    """Build trial company context."""
    if not isinstance(value, Mapping):
        return None
    try:
        return TrialCompanyContext.model_validate(dict(value))
    except ValidationError:
        return None


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
    (
        resolved_notice_version,
        resolved_notice_text,
        resolved_eval,
    ) = resolve_trial_ai_fields(
        notice_version=notice_version,
        notice_text=notice_text,
        eval_enabled_by_day=eval_enabled_by_day,
    )
    try:
        return TrialAIConfig.model_validate(
            {
                "noticeVersion": resolved_notice_version,
                "noticeText": resolved_notice_text,
                "evalEnabledByDay": resolved_eval,
                "promptOverrides": normalize_prompt_override_payload(
                    prompt_overrides_json
                ),
                "promptPackVersion": prompt_pack_version,
                "changesPendingRegeneration": changes_pending_regeneration,
                "activeScenarioSnapshot": active_scenario_snapshot,
                "pendingScenarioSnapshot": pending_scenario_snapshot,
            }
        )
    except ValidationError:
        return TrialAIConfig.model_validate(
            {
                "noticeVersion": AI_NOTICE_DEFAULT_VERSION,
                "noticeText": AI_NOTICE_DEFAULT_TEXT,
                "evalEnabledByDay": default_ai_eval_enabled_by_day(),
                "promptOverrides": normalize_prompt_override_payload(
                    prompt_overrides_json
                ),
                "promptPackVersion": prompt_pack_version,
                "changesPendingRegeneration": changes_pending_regeneration,
                "activeScenarioSnapshot": active_scenario_snapshot,
                "pendingScenarioSnapshot": pending_scenario_snapshot,
            }
        )


__all__ = ["build_trial_ai_config", "build_trial_company_context"]
