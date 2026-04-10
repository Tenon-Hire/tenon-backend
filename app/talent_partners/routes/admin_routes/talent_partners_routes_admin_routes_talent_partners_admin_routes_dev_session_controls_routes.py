"""Application module for Talent Partners routes admin routes Talent Partners admin routes dev session controls routes workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_windows_schema import (
    CurrentDayWindow,
    DayWindow,
)
from app.shared.auth.shared_auth_admin_api_key_utils import require_admin_key
from app.shared.database import get_session
from app.talent_partners.schemas.talent_partners_schemas_talent_partners_admin_ops_schema import (
    CandidateSessionDayWindowControlRequest,
    CandidateSessionDayWindowControlResponse,
)
from app.talent_partners.services import (
    talent_partners_services_talent_partners_admin_ops_service as admin_ops_service,
)

router = APIRouter()


def _build_current_day_window(payload: dict | None) -> CurrentDayWindow | None:
    if not isinstance(payload, dict):
        return None
    return CurrentDayWindow(
        dayIndex=int(payload["dayIndex"]),
        windowStartAt=payload["windowStartAt"],
        windowEndAt=payload["windowEndAt"],
        state=str(payload["state"]),
    )


@router.post(
    "/candidate_sessions/{candidate_session_id}/day_windows/control",
    response_model=CandidateSessionDayWindowControlResponse,
    status_code=status.HTTP_200_OK,
    summary="Control Candidate Session Day Windows",
    description=(
        "Local/test-only admin-keyed control that retimes a candidate session so a"
        " chosen day window is immediately usable for end-to-end validation."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Admin access required."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "The requested day-window control payload is invalid."
        },
    },
)
async def control_candidate_session_day_windows(
    candidate_session_id: Annotated[int, Path(..., gt=0)],
    payload: CandidateSessionDayWindowControlRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    _admin_key: Annotated[None, Depends(require_admin_key)],
) -> CandidateSessionDayWindowControlResponse:
    """Control candidate-session day windows for local/test validation."""
    result = await admin_ops_service.set_candidate_session_day_window(
        db,
        candidate_session_id=candidate_session_id,
        target_day_index=payload.targetDayIndex,
        reason=payload.reason,
        candidate_timezone=payload.candidateTimezone,
        minutes_already_open=payload.minutesAlreadyOpen,
        minutes_until_cutoff=payload.minutesUntilCutoff,
        window_start_local=payload.windowStartLocal,
        window_end_local=payload.windowEndLocal,
        dry_run=payload.dryRun,
    )
    return CandidateSessionDayWindowControlResponse(
        candidateSessionId=result.candidate_session_id,
        candidateStatus=result.candidate_status,
        status=result.status,
        targetDayIndex=result.target_day_index,
        candidateTimezone=result.candidate_timezone,
        scheduledStartAt=result.scheduled_start_at,
        scheduleLockedAt=result.schedule_locked_at,
        dayWindows=[
            DayWindow(
                dayIndex=int(item["dayIndex"]),
                windowStartAt=item["windowStartAt"],
                windowEndAt=item["windowEndAt"],
            )
            for item in result.day_windows
        ],
        currentDayWindow=_build_current_day_window(result.current_day_window),
        auditId=result.audit_id,
    )


__all__ = ["control_candidate_session_day_windows", "router"]
