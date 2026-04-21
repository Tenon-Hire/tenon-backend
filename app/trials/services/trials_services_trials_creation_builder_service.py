"""Application module for trials services trials creation builder service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import status

from app.shared.database.shared_database_models_model import Trial
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.constants.trials_constants_trials_blueprints_constants import (
    DEFAULT_5_DAY_DAY5_WINDOW_OVERRIDE,
)
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

DAY5_DAY_WINDOW_OVERRIDE_ERROR_CODE = "TRIAL_DAY5_WINDOW_OVERRIDE_INVALID"


def _resolve_preferred_language_framework(payload: Any) -> str | None:
    for key in ("preferredLanguageFramework", "preferred_language_framework"):
        value = getattr(payload, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _resolve_tech_stack(payload: Any, preferred_language_framework: str | None) -> str:
    raw_tech_stack = getattr(payload, "techStack", getattr(payload, "tech_stack", None))
    if isinstance(raw_tech_stack, str) and raw_tech_stack.strip():
        return raw_tech_stack.strip()
    if preferred_language_framework is not None:
        return preferred_language_framework
    return ""


def _resolve_day_window_overrides(
    *,
    day_window_overrides_enabled: bool,
    day_window_overrides_json: dict[str, dict[str, str]] | None,
) -> tuple[bool, dict[str, dict[str, str]]]:
    canonical_day5_override = DEFAULT_5_DAY_DAY5_WINDOW_OVERRIDE["5"]
    resolved_overrides: dict[str, dict[str, str]] = {
        str(day_index): {
            "startLocal": str(window.get("startLocal")),
            "endLocal": str(window.get("endLocal")),
        }
        for day_index, window in (day_window_overrides_json or {}).items()
        if isinstance(window, dict)
    }
    day5_override = resolved_overrides.get("5")
    if day5_override is not None and day5_override != canonical_day5_override:
        raise ApiError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "dayWindowOverrides['5'] must use the canonical Day 5 window of "
                "09:00 to 21:00 local"
            ),
            error_code=DAY5_DAY_WINDOW_OVERRIDE_ERROR_CODE,
            retryable=False,
            details={
                "field": "dayWindowOverrides.5",
                "expected": dict(canonical_day5_override),
                "actual": dict(day5_override),
            },
        )
    resolved_overrides.setdefault("5", dict(canonical_day5_override))
    return bool(day_window_overrides_enabled or resolved_overrides), resolved_overrides


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
    (
        day_window_overrides_enabled,
        day_window_overrides_json,
    ) = _resolve_day_window_overrides(
        day_window_overrides_enabled=day_window_overrides_enabled,
        day_window_overrides_json=day_window_overrides_json,
    )
    preferred_language_framework = _resolve_preferred_language_framework(payload)
    company_context = extract_company_context(payload)
    if preferred_language_framework is not None:
        company_context = {
            **(company_context or {}),
            "preferredLanguageFramework": preferred_language_framework,
        }
    sim = Trial(
        title=payload.title,
        role=payload.role,
        tech_stack=_resolve_tech_stack(payload, preferred_language_framework),
        seniority=normalized_seniority or raw_seniority,
        focus=getattr(payload, "focus", None) or "",
        company_context=company_context,
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
