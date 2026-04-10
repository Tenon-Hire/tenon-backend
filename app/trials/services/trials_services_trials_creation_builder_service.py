"""Application module for trials services trials creation builder service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.shared.database.shared_database_models_model import Trial
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_GENERATING,
)
from app.trials.schemas.trials_schemas_trials_core_schema import (
    normalize_role_level,
    resolve_trial_ai_fields,
)

from .trials_services_trials_creation_extractors_service import (
    extract_ai_fields,
    extract_company_context,
    extract_day_window_config,
)
from .trials_services_trials_template_keys_service import resolve_template_key


def build_trial_for_create(
    payload: Any, user: Any
) -> tuple[Trial, str, dict[str, bool]]:
    """Build trial for create."""
    template_key = resolve_template_key(payload)
    started_at = datetime.now(UTC)
    (
        ai_notice_version,
        ai_notice_text,
        ai_eval_enabled_by_day,
        ai_prompt_overrides_json,
    ) = extract_ai_fields(payload)
    (
        resolved_notice_version,
        resolved_notice_text,
        resolved_eval_by_day,
    ) = resolve_trial_ai_fields(
        notice_version=ai_notice_version,
        notice_text=ai_notice_text,
        eval_enabled_by_day=ai_eval_enabled_by_day,
    )
    raw_seniority = getattr(payload, "seniority", None)
    normalized_seniority = normalize_role_level(raw_seniority)
    (
        day_window_start_local,
        day_window_end_local,
        day_window_overrides_enabled,
        day_window_overrides_json,
    ) = extract_day_window_config(payload)
    sim = Trial(
        title=payload.title,
        role=payload.role,
        tech_stack=getattr(payload, "techStack", getattr(payload, "tech_stack", "")),
        seniority=normalized_seniority or raw_seniority,
        focus=payload.focus,
        company_context=extract_company_context(payload),
        ai_prompt_overrides_json=ai_prompt_overrides_json,
        ai_notice_version=resolved_notice_version,
        ai_notice_text=resolved_notice_text,
        ai_eval_enabled_by_day=resolved_eval_by_day,
        day_window_start_local=day_window_start_local,
        day_window_end_local=day_window_end_local,
        day_window_overrides_enabled=day_window_overrides_enabled,
        day_window_overrides_json=day_window_overrides_json,
        scenario_template=template_key,
        company_id=user.company_id,
        created_by=user.id,
        template_key=template_key,
        status=TRIAL_STATUS_GENERATING,
        generating_at=started_at,
    )
    return sim, resolved_notice_version, resolved_eval_by_day
