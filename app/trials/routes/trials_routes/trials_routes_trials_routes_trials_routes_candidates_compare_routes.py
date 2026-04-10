"""Application module for trials routes trials routes trials routes candidates compare routes workflows."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import User
from app.trials import services as sim_service
from app.trials.schemas.trials_schemas_trials_compare_schema import (
    TrialCandidatesCompareResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/{trial_id}/candidates/compare",
    response_model=TrialCandidatesCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="List Trial Candidates Compare",
    description=(
        "Return side-by-side candidate progress and scoring signals for a"
        " Talent Partner-owned trial."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Trial not found."},
    },
)
async def list_trial_candidates_compare(
    trial_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> TrialCandidatesCompareResponse:
    """Return trial candidates compare."""
    ensure_talent_partner(user)
    started_at = perf_counter()
    payload = await sim_service.list_candidates_compare_summary(
        db,
        trial_id=trial_id,
        user=user,
    )
    latency_ms = int((perf_counter() - started_at) * 1000)
    logger.info(
        "Trial candidates compare fetched trialId=%s talentPartnerId=%s rowCount=%s latencyMs=%s",
        trial_id,
        user.id,
        len(payload["candidates"]),
        latency_ms,
    )
    return TrialCandidatesCompareResponse(**payload)


__all__ = ["router", "list_trial_candidates_compare"]
