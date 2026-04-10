"""Application module for trials services trials scenario payload builder service workflows."""

from __future__ import annotations

from typing import Any

from app.trials.schemas.trials_schemas_trials_core_schema import (
    build_trial_ai_config,
    build_trial_company_context,
    normalize_role_level,
)

__all__ = ["build_scenario_generation_payload"]


def build_scenario_generation_payload(trial: Any) -> dict[str, Any]:
    """Build a safe, structured payload for scenario-generation workers."""
    talent_partner_context: dict[str, Any] = {}

    role_level = normalize_role_level(getattr(trial, "seniority", None))
    if role_level is not None:
        talent_partner_context["seniority"] = role_level

    focus_notes = getattr(trial, "focus", None)
    if focus_notes is not None:
        talent_partner_context["focus"] = focus_notes

    company_context = build_trial_company_context(
        getattr(trial, "company_context", None)
    )
    if company_context is not None:
        talent_partner_context["companyContext"] = company_context.model_dump(
            by_alias=True
        )

    ai_config = build_trial_ai_config(
        notice_version=getattr(trial, "ai_notice_version", None),
        notice_text=getattr(trial, "ai_notice_text", None),
        eval_enabled_by_day=getattr(trial, "ai_eval_enabled_by_day", None),
        prompt_overrides_json=getattr(trial, "ai_prompt_overrides_json", None),
    )
    if ai_config is not None:
        talent_partner_context["ai"] = ai_config.model_dump(by_alias=True)

    return {
        "trialId": getattr(trial, "id", None),
        "templateKey": getattr(trial, "template_key", None),
        "scenarioTemplate": getattr(trial, "scenario_template", None),
        "talentPartnerContext": talent_partner_context,
    }
