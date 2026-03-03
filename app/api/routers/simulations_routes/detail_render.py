from __future__ import annotations

from fastapi import status

from app.core.errors import ApiError
from app.domains.simulations import service as sim_service
from app.domains.simulations.schemas import (
    ScenarioVersionSummary,
    SimulationDetailResponse,
    SimulationDetailTask,
)


def _normalized_status_or_error(raw_status: str | None) -> str:
    normalized = sim_service.normalize_simulation_status(raw_status)
    if normalized is not None:
        return normalized
    raise ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Invalid simulation status.",
        error_code="SIMULATION_STATUS_INVALID",
        retryable=False,
        details={"status": raw_status},
    )


def render_simulation_detail(sim, tasks) -> SimulationDetailResponse:
    raw_status = getattr(sim, "status", None)
    status_value = _normalized_status_or_error(raw_status)
    return SimulationDetailResponse(
        id=sim.id,
        title=sim.title,
        templateKey=sim.template_key,
        role=sim.role,
        techStack=sim.tech_stack,
        focus=sim.focus,
        scenario=sim.scenario_template,
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
