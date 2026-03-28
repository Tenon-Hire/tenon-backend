"""Application module for candidates candidate sessions services candidates candidate sessions invite items service workflows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_progress_service import (
    progress_snapshot,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_fields_service import (
    schedule_payload_for_candidate_session,
)
from app.candidates.candidate_sessions.utils.candidates_candidate_sessions_utils_candidates_candidate_sessions_progress_utils import (
    summarize_progress,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateInviteListItem,
    ProgressSummary,
)
from app.shared.database.shared_database_models_model import Task


async def build_invite_item(
    db: AsyncSession,
    candidate_session,
    *,
    now: datetime,
    last_submitted_map: dict[int, datetime | None],
    tasks_loader: Callable[[int], Awaitable[list[Task]]],
    completed_ids: set[int] | None = None,
) -> CandidateInviteListItem:
    """Build invite item."""
    expires_at = candidate_session.expires_at
    expires_at = (
        expires_at.replace(tzinfo=UTC)
        if expires_at and expires_at.tzinfo is None
        else expires_at
    )
    is_expired = bool(expires_at and expires_at < now)
    task_list = await tasks_loader(candidate_session.simulation_id)
    if completed_ids is None:
        _, completed_ids, _, completed, total, _ = await progress_snapshot(
            db, candidate_session, tasks=task_list
        )
    else:
        completed, total, _ = summarize_progress(len(task_list), completed_ids)
    last_submitted_at = last_submitted_map.get(candidate_session.id)
    last_activity = (
        last_submitted_at
        or candidate_session.completed_at
        or candidate_session.started_at
    )
    schedule_payload = schedule_payload_for_candidate_session(
        candidate_session, now_utc=now
    )
    sim = candidate_session.simulation
    company_name = getattr(sim.company, "name", None) if sim else None
    return CandidateInviteListItem(
        candidateSessionId=candidate_session.id,
        simulationId=sim.id if sim else candidate_session.simulation_id,
        simulationTitle=sim.title if sim else "",
        role=sim.role if sim else "",
        companyName=company_name,
        status=candidate_session.status,
        progress=ProgressSummary(completed=completed, total=total),
        lastActivityAt=last_activity,
        inviteCreatedAt=getattr(candidate_session, "created_at", None),
        expiresAt=candidate_session.expires_at,
        inviteToken=candidate_session.token,
        isExpired=is_expired,
        scheduledStartAt=schedule_payload["scheduledStartAt"],
        candidateTimezone=schedule_payload["candidateTimezone"],
        dayWindows=schedule_payload["dayWindows"],
        scheduleLockedAt=schedule_payload["scheduleLockedAt"],
        currentDayWindow=schedule_payload["currentDayWindow"],
    )
