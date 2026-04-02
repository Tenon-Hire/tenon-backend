"""Application module for simulations routes simulations routes simulations routes detail routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import build_ai_policy_snapshot
from app.recruiters.repositories.companies.recruiters_repositories_companies_recruiters_companies_core_model import (
    Company,
)
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import ScenarioVersion
from app.submissions.repositories.precommit_bundles import (
    repository_lookup as bundle_lookup_repo,
)
from app.simulations import services as sim_service
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_detail_render_routes import (
    render_simulation_detail,
)
from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    SimulationDetailResponse,
)
from app.simulations.services.simulations_services_simulations_codespace_specializer_service import (
    has_coding_tasks,
)

router = APIRouter()


async def _load_scenario_version(
    db: AsyncSession, scenario_version_id: int | None
) -> ScenarioVersion | None:
    if scenario_version_id is None:
        return None
    return await db.scalar(
        select(ScenarioVersion).where(ScenarioVersion.id == scenario_version_id)
    )


async def _resolve_bundle_status(
    db: AsyncSession,
    *,
    sim,
    tasks,
    scenario_version,
) -> str | None:
    if scenario_version is None or not has_coding_tasks(tasks):
        return None
    template_key = (
        str(getattr(scenario_version, "template_key", "") or "").strip()
        or str(getattr(sim, "template_key", "") or "").strip()
    )
    if not template_key:
        return None
    bundle = await bundle_lookup_repo.get_by_scenario_and_template(
        db,
        scenario_version_id=scenario_version.id,
        template_key=template_key,
    )
    return getattr(bundle, "status", None) or "missing"


@router.get(
    "/{simulation_id}",
    response_model=SimulationDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_simulation_detail(
    simulation_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Return a simulation detail view for recruiters."""
    ensure_recruiter_or_none(user)
    sim, tasks = await sim_service.require_owned_simulation_with_tasks(
        db, simulation_id, user.id
    )
    active_scenario_version = await sim_service.get_active_scenario_version(
        db, simulation_id
    )
    pending_scenario_version = await _load_scenario_version(
        db, getattr(sim, "pending_scenario_version_id", None)
    )
    company = await db.scalar(select(Company).where(Company.id == sim.company_id))
    current_ai_policy_snapshot_json = build_ai_policy_snapshot(
        simulation=sim,
        company_prompt_overrides_json=getattr(
            company, "ai_prompt_overrides_json", None
        ),
        simulation_prompt_overrides_json=getattr(
            sim, "ai_prompt_overrides_json", None
        ),
    )
    active_bundle_status = await _resolve_bundle_status(
        db,
        sim=sim,
        tasks=tasks,
        scenario_version=active_scenario_version,
    )
    pending_bundle_status = await _resolve_bundle_status(
        db,
        sim=sim,
        tasks=tasks,
        scenario_version=pending_scenario_version,
    )
    return render_simulation_detail(
        sim,
        tasks,
        active_scenario_version,
        pending_scenario_version=pending_scenario_version,
        current_ai_policy_snapshot_json=current_ai_policy_snapshot_json,
        active_bundle_status=active_bundle_status,
        pending_bundle_status=pending_bundle_status,
    )
