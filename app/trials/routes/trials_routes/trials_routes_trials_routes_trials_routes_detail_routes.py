"""Application module for trials routes trials routes trials routes detail routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIPolicySnapshotError
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import Job, ScenarioVersion
from app.shared.jobs.shared_jobs_failure_summaries_service import (
    trial_background_failures,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials import services as trial_service
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_detail_render_routes import (
    render_trial_detail,
)
from app.trials.schemas.trials_schemas_trials_core_schema import (
    TrialDetailResponse,
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
    sim, tasks = await trial_service.require_owned_trial_with_tasks(
        db, trial_id, user.id
    )
    active_scenario_version = await trial_service.get_active_scenario_version(
        db, trial_id
    )
    pending_scenario_version = await _load_scenario_version(
        db, getattr(sim, "pending_scenario_version_id", None)
    )
    current_snapshot_source = pending_scenario_version or active_scenario_version
    current_ai_policy_snapshot_json = getattr(
        current_snapshot_source, "ai_policy_snapshot_json", None
    )
    scenario_generation_job = await _load_latest_scenario_generation_job(
        db,
        trial_id=trial_id,
        company_id=sim.company_id,
    )
    background_failures = await trial_background_failures(
        db,
        trial_id=trial_id,
        company_id=sim.company_id,
    )
    try:
        return render_trial_detail(
            sim,
            tasks,
            active_scenario_version,
            pending_scenario_version=pending_scenario_version,
            current_ai_policy_snapshot_json=current_ai_policy_snapshot_json,
            active_bundle_status=None,
            pending_bundle_status=None,
            scenario_generation_job=scenario_generation_job,
            background_failures=background_failures,
        )
    except AIPolicySnapshotError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Frozen AI policy snapshot is invalid.",
            error_code=getattr(
                exc, "error_code", "scenario_version_ai_policy_snapshot_invalid"
            ),
            retryable=False,
            details=getattr(exc, "details", {}),
        ) from exc
