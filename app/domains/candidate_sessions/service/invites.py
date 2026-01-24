from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import Task
from app.domains.candidate_sessions import repository as cs_repo
from app.domains.candidate_sessions.schemas import (
    CandidateInviteListItem,
    ProgressSummary,
)
from app.domains.candidate_sessions.service.progress import progress_snapshot
from app.infra.security.principal import Principal


async def invite_list_for_principal(
    db: AsyncSession, principal: Principal
) -> list[CandidateInviteListItem]:
    email = (principal.email or "").strip().lower()
    sessions = await cs_repo.list_for_email(db, email)
    items: list[CandidateInviteListItem] = []
    now = datetime.now(UTC)
    session_ids = [cs.id for cs in sessions]
    last_submitted_map = await cs_repo.last_submission_at_bulk(db, session_ids)
    tasks_cache: dict[int, list[Task]] = {}

    async def _tasks_for_simulation(simulation_id: int) -> list[Task]:
        if simulation_id not in tasks_cache:
            tasks_cache[simulation_id] = await cs_repo.tasks_for_simulation(
                db, simulation_id
            )
        return tasks_cache[simulation_id]

    for cs in sessions:
        expires_at = cs.expires_at
        is_expired = False
        if expires_at is not None:
            exp = (
                expires_at.replace(tzinfo=UTC)
                if expires_at.tzinfo is None
                else expires_at
            )
            is_expired = exp < now
        task_list = await _tasks_for_simulation(cs.simulation_id)
        progress_tasks = await progress_snapshot(db, cs, tasks=task_list)
        (
            _tasks,
            completed_ids,
            _current,
            completed,
            total,
            _is_complete,
        ) = progress_tasks
        last_submitted_at = last_submitted_map.get(cs.id)
        last_activity = last_submitted_at or cs.completed_at or cs.started_at
        sim = cs.simulation
        company_name = getattr(sim.company, "name", None) if sim else None
        items.append(
            CandidateInviteListItem(
                candidateSessionId=cs.id,
                simulationId=sim.id if sim else cs.simulation_id,
                simulationTitle=sim.title if sim else "",
                role=sim.role if sim else "",
                companyName=company_name,
                status=cs.status,
                progress=ProgressSummary(completed=completed, total=total),
                lastActivityAt=last_activity,
                inviteCreatedAt=getattr(cs, "created_at", None),
                expiresAt=cs.expires_at,
                inviteToken=cs.token,
                isExpired=is_expired,
            )
        )
    return items
