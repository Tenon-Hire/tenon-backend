"""Application module for simulations routes simulations routes simulations routes list simulations routes workflows."""

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
    SimulationListItem,
    build_simulation_ai_config,
    build_simulation_company_context,
    normalize_role_level,
)

router = APIRouter(prefix="/simulations")


@router.get("", response_model=list[SimulationListItem], status_code=status.HTTP_200_OK)
async def list_simulations(
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
    includeTerminated: bool = False,
):
    """List simulations for recruiter dashboard (scoped to current user)."""
    ensure_recruiter_or_none(user)
    rows = await sim_service.list_simulations(
        db, user.id, include_terminated=includeTerminated
    )
    return [
        SimulationListItem(
            id=sim.id,
            title=sim.title,
            role=sim.role,
            techStack=sim.tech_stack,
            seniority=normalize_role_level(getattr(sim, "seniority", None))
            or getattr(sim, "seniority", None),
            companyContext=build_simulation_company_context(
                getattr(sim, "company_context", None)
            ),
            ai=build_simulation_ai_config(
                notice_version=getattr(sim, "ai_notice_version", None),
                notice_text=getattr(sim, "ai_notice_text", None),
                eval_enabled_by_day=getattr(sim, "ai_eval_enabled_by_day", None),
            ),
            templateKey=sim.template_key,
            status=sim_service.normalize_simulation_status_or_raise(
                getattr(sim, "status", None)
            ),
            activatedAt=getattr(sim, "activated_at", None),
            terminatedAt=getattr(sim, "terminated_at", None),
            scenarioVersionSummary=ScenarioVersionSummary(
                templateKey=getattr(sim, "template_key", None),
                scenarioTemplate=getattr(sim, "scenario_template", None),
            ),
            createdAt=sim.created_at,
            numCandidates=int(num_candidates),
        )
        for sim, num_candidates in rows
    ]
