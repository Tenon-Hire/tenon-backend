"""Application module for trials routes trials routes trials routes scenario routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.shared.database import get_session
from app.trials import services as sim_service
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_rate_limits_routes import (
    enforce_scenario_regenerate_limit,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_scenario_payloads_routes import (
    build_active_update_response,
    build_approve_response,
    build_patch_response,
    build_regenerate_response,
    normalize_active_updates,
    normalize_patch_updates,
)
from app.trials.schemas.trials_schemas_trials_core_schema import (
    ScenarioActiveUpdateRequest,
    ScenarioActiveUpdateResponse,
    ScenarioApproveResponse,
    ScenarioRegenerateResponse,
    ScenarioVersionPatchRequest,
    ScenarioVersionPatchResponse,
)

router = APIRouter()


@router.post(
    "/{trial_id}/scenario/regenerate",
    response_model=ScenarioRegenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate Scenario Version",
    description=(
        "Request a regenerated scenario version for a trial and return the"
        " created job reference."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Trial not found."},
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "description": "Scenario regeneration rate limit exceeded."
        },
    },
)
async def regenerate_scenario_version(
    trial_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Regenerate scenario version."""
    ensure_talent_partner_or_none(user)
    enforce_scenario_regenerate_limit(request, user.id)
    (
        _trial,
        scenario_version,
        scenario_job,
    ) = await sim_service.request_scenario_regeneration(
        db,
        trial_id=trial_id,
        actor_user_id=user.id,
    )
    return build_regenerate_response(scenario_version, scenario_job)


@router.post(
    "/{trial_id}/scenario/{scenario_version_id}/approve",
    response_model=ScenarioApproveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Scenario Version",
    description=("Approve a scenario version and promote it for active trial usage."),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {
            "description": "Trial or scenario version not found."
        },
    },
)
async def approve_scenario_version(
    trial_id: int,
    scenario_version_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Approve scenario version."""
    ensure_talent_partner_or_none(user)
    trial, scenario_version = await sim_service.approve_scenario_version(
        db,
        trial_id=trial_id,
        scenario_version_id=scenario_version_id,
        actor_user_id=user.id,
    )
    return build_approve_response(trial, scenario_version)


@router.patch(
    "/{trial_id}/scenario/active",
    response_model=ScenarioActiveUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Active Scenario Version",
    description=(
        "Update active scenario metadata and assignment fields for the" " trial."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Trial not found."},
    },
)
async def update_active_scenario_version(
    trial_id: int,
    payload: ScenarioActiveUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Update active scenario version."""
    ensure_talent_partner_or_none(user)
    scenario_version = await sim_service.update_active_scenario_version(
        db,
        trial_id=trial_id,
        actor_user_id=user.id,
        updates=normalize_active_updates(payload),
    )
    return build_active_update_response(trial_id, scenario_version)


@router.patch(
    "/{trial_id}/scenario/{scenario_version_id}",
    response_model=ScenarioVersionPatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Patch Scenario Version",
    description=(
        "Patch editable scenario version content and return the updated"
        " scenario payload."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {
            "description": "Trial or scenario version not found."
        },
    },
)
async def patch_scenario_version(
    trial_id: int,
    scenario_version_id: int,
    payload: ScenarioVersionPatchRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Patch scenario version."""
    ensure_talent_partner_or_none(user)
    scenario_version = await sim_service.patch_scenario_version(
        db,
        trial_id=trial_id,
        scenario_version_id=scenario_version_id,
        actor_user_id=user.id,
        updates=normalize_patch_updates(payload),
    )
    return build_patch_response(scenario_version)


__all__ = [
    "approve_scenario_version",
    "patch_scenario_version",
    "regenerate_scenario_version",
    "router",
    "update_active_scenario_version",
]
