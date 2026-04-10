"""Application module for trials routes trials routes trials routes update routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.shared.database import get_session
from app.trials import services as sim_service
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_detail_render_routes import (
    render_trial_detail,
)
from app.trials.schemas.trials_schemas_trials_core_schema import (
    TrialDetailResponse,
    TrialUpdate,
)

router = APIRouter()


@router.put(
    "/{trial_id}",
    response_model=TrialDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def update_trial(
    trial_id: int,
    payload: TrialUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Update mutable trial configuration."""
    ensure_talent_partner_or_none(user)
    trial, tasks = await sim_service.update_trial(
        db,
        trial_id=trial_id,
        actor_user_id=user.id,
        payload=payload,
    )
    active_scenario_version = await sim_service.get_active_scenario_version(
        db,
        trial_id,
    )
    return render_trial_detail(trial, tasks, active_scenario_version)


__all__ = ["router", "update_trial"]
