"""Application module for trials routes trials routes trials routes detail routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import build_ai_policy_snapshot
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import Job, ScenarioVersion
from app.submissions.repositories.precommit_bundles import (
    repository_lookup as bundle_lookup_repo,
)
from app.talent_partners.repositories.companies.talent_partners_repositories_companies_talent_partners_companies_core_model import (
    Company,
)
from app.trials import services as sim_service
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_detail_render_routes import (
    render_trial_detail,
)
from app.trials.schemas.trials_schemas_trials_core_schema import (
    TrialDetailResponse,
)
from app.trials.services.trials_services_trials_codespace_specializer_service import (
    has_coding_tasks,
)
from app.trials.services.trials_services_trials_scenario_generation_constants import (
    SCENARIO_GENERATION_JOB_TYPE,
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


async def _load_latest_scenario_generation_job(
    db: AsyncSession, *, trial_id: int, company_id: int
) -> Job | None:
    stmt = (
        select(Job)
        .where(
            Job.company_id == company_id,
            Job.job_type == SCENARIO_GENERATION_JOB_TYPE,
            Job.correlation_id.like(f"trial:{trial_id}%"),
        )
        .order_by(desc(Job.created_at), desc(Job.updated_at))
    )
    return await db.scalar(stmt)


@router.get(
    "/{trial_id}",
    response_model=TrialDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_trial_detail(
    trial_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Return a trial detail view for talent_partners."""
    ensure_talent_partner_or_none(user)
    sim, tasks = await sim_service.require_owned_trial_with_tasks(db, trial_id, user.id)
    active_scenario_version = await sim_service.get_active_scenario_version(
        db, trial_id
    )
    pending_scenario_version = await _load_scenario_version(
        db, getattr(sim, "pending_scenario_version_id", None)
    )
    company = await db.scalar(select(Company).where(Company.id == sim.company_id))
    current_ai_policy_snapshot_json = build_ai_policy_snapshot(
        trial=sim,
        company_prompt_overrides_json=getattr(
            company, "ai_prompt_overrides_json", None
        ),
        trial_prompt_overrides_json=getattr(sim, "ai_prompt_overrides_json", None),
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
    scenario_generation_job = await _load_latest_scenario_generation_job(
        db,
        trial_id=trial_id,
        company_id=sim.company_id,
    )
    return render_trial_detail(
        sim,
        tasks,
        active_scenario_version,
        pending_scenario_version=pending_scenario_version,
        current_ai_policy_snapshot_json=current_ai_policy_snapshot_json,
        active_bundle_status=active_bundle_status,
        pending_bundle_status=pending_bundle_status,
        scenario_generation_job=scenario_generation_job,
    )
