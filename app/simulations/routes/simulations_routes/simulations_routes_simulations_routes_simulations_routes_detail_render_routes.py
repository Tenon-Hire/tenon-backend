"""Application module for simulations routes simulations routes simulations routes detail render routes workflows."""

from __future__ import annotations

from app.simulations import services as sim_service
from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    ScenarioVersionSummary,
    SimulationDetailResponse,
    SimulationDetailScenario,
    SimulationDetailTask,
    build_simulation_ai_config,
    build_simulation_company_context,
    normalize_role_level,
)


def render_simulation_detail(
    sim, tasks, active_scenario_version
) -> SimulationDetailResponse:
    """Render simulation detail."""
    raw_status = getattr(sim, "status", None)
    status_value = sim_service.normalize_simulation_status_or_raise(raw_status)
    return SimulationDetailResponse(
        id=sim.id,
        title=sim.title,
        templateKey=sim.template_key,
        role=sim.role,
        seniority=normalize_role_level(getattr(sim, "seniority", None))
        or getattr(sim, "seniority", None),
        techStack=sim.tech_stack,
        focus=sim.focus,
        companyContext=build_simulation_company_context(
            getattr(sim, "company_context", None)
        ),
        ai=build_simulation_ai_config(
            notice_version=getattr(sim, "ai_notice_version", None),
            notice_text=getattr(sim, "ai_notice_text", None),
            eval_enabled_by_day=getattr(sim, "ai_eval_enabled_by_day", None),
        ),
        activeScenarioVersionId=getattr(sim, "active_scenario_version_id", None),
        pendingScenarioVersionId=getattr(sim, "pending_scenario_version_id", None),
        scenario=(
            SimulationDetailScenario(
                id=active_scenario_version.id,
                versionIndex=active_scenario_version.version_index,
                status=active_scenario_version.status,
                lockedAt=active_scenario_version.locked_at,
                storylineMd=active_scenario_version.storyline_md,
                taskPromptsJson=active_scenario_version.task_prompts_json,
                rubricJson=active_scenario_version.rubric_json,
                notes=active_scenario_version.focus_notes,
                modelName=active_scenario_version.model_name,
                modelVersion=active_scenario_version.model_version,
                promptVersion=active_scenario_version.prompt_version,
                rubricVersion=active_scenario_version.rubric_version,
            )
            if active_scenario_version is not None
            else None
        ),
        status=status_value,
        generatingAt=getattr(sim, "generating_at", None),
        readyForReviewAt=getattr(sim, "ready_for_review_at", None),
        activatedAt=getattr(sim, "activated_at", None),
        terminatedAt=getattr(sim, "terminated_at", None),
        scenarioVersionSummary=ScenarioVersionSummary(
            templateKey=getattr(sim, "template_key", None),
            scenarioTemplate=getattr(sim, "scenario_template", None),
        ),
        tasks=[
            SimulationDetailTask(
                dayIndex=task.day_index,
                title=task.title,
                type=task.type,
                description=task.description,
                rubric=None,
                maxScore=task.max_score,
                templateRepoFullName=(
                    task.template_repo
                    if task.day_index in {2, 3} and task.template_repo
                    else None
                ),
            )
            for task in tasks
        ],
    )
