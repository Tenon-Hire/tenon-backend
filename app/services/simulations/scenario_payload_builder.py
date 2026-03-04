from __future__ import annotations

from typing import Any

from app.domains.simulations.schemas import (
    build_simulation_ai_config,
    build_simulation_company_context,
    normalize_role_level,
)

__all__ = ["build_scenario_generation_payload"]


def build_scenario_generation_payload(simulation: Any) -> dict[str, Any]:
    """Build a safe, structured payload for scenario-generation workers."""
    recruiter_context: dict[str, Any] = {}

    role_level = normalize_role_level(getattr(simulation, "seniority", None))
    if role_level is not None:
        recruiter_context["seniority"] = role_level

    focus_notes = getattr(simulation, "focus", None)
    if focus_notes is not None:
        recruiter_context["focus"] = focus_notes

    company_context = build_simulation_company_context(
        getattr(simulation, "company_context", None)
    )
    if company_context is not None:
        recruiter_context["companyContext"] = company_context.model_dump(by_alias=True)

    ai_config = build_simulation_ai_config(
        notice_version=getattr(simulation, "ai_notice_version", None),
        notice_text=getattr(simulation, "ai_notice_text", None),
        eval_enabled_by_day=getattr(simulation, "ai_eval_enabled_by_day", None),
    )
    if ai_config is not None:
        recruiter_context["ai"] = ai_config.model_dump(by_alias=True)

    return {
        "simulationId": getattr(simulation, "id", None),
        "templateKey": getattr(simulation, "template_key", None),
        "scenarioTemplate": getattr(simulation, "scenario_template", None),
        "recruiterContext": recruiter_context,
    }
