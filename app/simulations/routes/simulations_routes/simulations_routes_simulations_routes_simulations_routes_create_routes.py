"""Application module for simulations routes simulations routes simulations routes create routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.shared.database import get_session
from app.simulations import services as sim_service
from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    ScenarioVersionSummary,
    SimulationCreate,
    SimulationCreateResponse,
    TaskOut,
    build_simulation_ai_config,
    build_simulation_company_context,
    normalize_role_level,
)

router = APIRouter(prefix="/simulations")


@router.post(
    "", response_model=SimulationCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_simulation(
    payload: SimulationCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Create a simulation and seed default tasks."""
    ensure_recruiter_or_none(user)
    sim, created_tasks, scenario_job = await sim_service.create_simulation_with_tasks(
        db, payload, user
    )
    raw_status = getattr(sim, "status", None)
    return SimulationCreateResponse(
        id=sim.id,
        title=sim.title,
        role=sim.role,
        techStack=sim.tech_stack,
        seniority=normalize_role_level(sim.seniority) or sim.seniority,
        focus=sim.focus,
        companyContext=build_simulation_company_context(
            getattr(sim, "company_context", None)
        ),
        ai=build_simulation_ai_config(
            notice_version=getattr(sim, "ai_notice_version", None),
            notice_text=getattr(sim, "ai_notice_text", None),
            eval_enabled_by_day=getattr(sim, "ai_eval_enabled_by_day", None),
            prompt_overrides_json=getattr(sim, "ai_prompt_overrides_json", None),
        ),
        templateKey=sim.template_key,
        status=sim_service.normalize_simulation_status_or_raise(raw_status),
        generatingAt=getattr(sim, "generating_at", None),
        readyForReviewAt=getattr(sim, "ready_for_review_at", None),
        activatedAt=getattr(sim, "activated_at", None),
        terminatedAt=getattr(sim, "terminated_at", None),
        scenarioVersionSummary=ScenarioVersionSummary(
            templateKey=getattr(sim, "template_key", None),
            scenarioTemplate=getattr(sim, "scenario_template", None),
        ),
        scenarioGenerationJobId=str(scenario_job.id),
        tasks=[
            TaskOut(id=t.id, day_index=t.day_index, type=t.type, title=t.title)
            for t in created_tasks
        ],
    )
