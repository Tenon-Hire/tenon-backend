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
from app.shared.database.shared_database_models_model import Task, User
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)


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
    task_list = await tasks_loader(candidate_session.trial_id)
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
    sim = candidate_session.trial
    company_name = getattr(sim.company, "name", None) if sim else None
    terminated_at = getattr(sim, "terminated_at", None) if sim else None
    is_terminated = bool(
        sim
        and (
            getattr(sim, "status", None) == TRIAL_STATUS_TERMINATED
            or terminated_at is not None
        )
    )
    report_ready = bool(getattr(candidate_session, "winoe_report", None))
    talent_partner_name = None
    talent_partner_email = None
    talent_partner_id = getattr(sim, "created_by", None) if sim else None
    if talent_partner_id:
        talent_partner = await db.get(User, talent_partner_id)
        if talent_partner is not None:
            talent_partner_name = getattr(talent_partner, "name", None) or getattr(
                talent_partner, "email", None
            )
            talent_partner_email = getattr(talent_partner, "email", None)
    return CandidateInviteListItem(
        candidateSessionId=candidate_session.id,
        trialId=sim.id if sim else candidate_session.trial_id,
        trialTitle=sim.title if sim else "",
        role=sim.role if sim else "",
        companyName=company_name,
        talentPartnerName=talent_partner_name,
        talentPartnerEmail=talent_partner_email,
        status=candidate_session.status,
        progress=ProgressSummary(completed=completed, total=total),
        lastActivityAt=last_activity,
        inviteCreatedAt=getattr(candidate_session, "created_at", None),
        expiresAt=candidate_session.expires_at,
        inviteToken=candidate_session.token,
        isExpired=is_expired,
        hasReport=report_ready,
        reportReady=report_ready,
        terminatedAt=terminated_at,
        isTerminated=is_terminated,
        scheduledStartAt=schedule_payload["scheduledStartAt"],
        candidateTimezone=schedule_payload["candidateTimezone"],
        githubUsername=getattr(candidate_session, "github_username", None),
        dayWindows=schedule_payload["dayWindows"],
        scheduleLockedAt=schedule_payload["scheduleLockedAt"],
        currentDayWindow=schedule_payload["currentDayWindow"],
    )
