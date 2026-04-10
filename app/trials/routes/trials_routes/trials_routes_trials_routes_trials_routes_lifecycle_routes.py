"""Application module for trials routes trials routes trials routes lifecycle routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.shared.database import get_session
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials import services as sim_service
from app.trials.schemas.trials_schemas_trials_core_schema import (
    TrialActivateResponse,
    TrialLifecycleRequest,
    TrialTerminateResponse,
)

router = APIRouter()


def _require_confirmation(payload: TrialLifecycleRequest) -> None:
    if payload.confirm:
        return
    raise ApiError(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="confirm=true is required",
        error_code="TRIAL_CONFIRMATION_REQUIRED",
        retryable=False,
        details={},
    )


@router.post(
    "/{trial_id}/activate",
    response_model=TrialActivateResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate Trial",
    description=(
        "Transition a trial into the active state once Talent Partner confirms"
        " readiness."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Activation confirmation missing."
        },
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Trial not found."},
    },
)
async def activate_trial(
    trial_id: int,
    payload: TrialLifecycleRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Activate trial."""
    ensure_talent_partner_or_none(user)
    _require_confirmation(payload)
    trial = await sim_service.activate_trial(
        db, trial_id=trial_id, actor_user_id=user.id
    )
    status_value = sim_service.normalize_trial_status_or_raise(trial.status)
    return TrialActivateResponse(
        trialId=trial.id,
        status=status_value,
        activatedAt=trial.activated_at,
    )


@router.post(
    "/{trial_id}/terminate",
    response_model=TrialTerminateResponse,
    status_code=status.HTTP_200_OK,
    summary="Terminate Trial",
    description=(
        "Terminate an active trial and enqueue workspace cleanup jobs for"
        " associated candidate workspaces."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Termination confirmation missing."
        },
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Trial not found."},
    },
)
async def terminate_trial(
    trial_id: int,
    payload: TrialLifecycleRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Terminate trial."""
    ensure_talent_partner_or_none(user)
    _require_confirmation(payload)
    terminated = await sim_service.terminate_trial_with_cleanup(
        db,
        trial_id=trial_id,
        actor_user_id=user.id,
        reason=payload.reason,
    )
    trial = terminated.trial
    status_value = sim_service.normalize_trial_status_or_raise(trial.status)
    return TrialTerminateResponse(
        trialId=trial.id,
        status=status_value,
        terminatedAt=trial.terminated_at,
        cleanupJobIds=terminated.cleanup_job_ids,
    )
