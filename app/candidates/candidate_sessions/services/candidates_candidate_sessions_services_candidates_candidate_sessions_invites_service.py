"""Application module for candidates candidate sessions services candidates candidate sessions invites service workflows."""

from __future__ import annotations

import inspect

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_invite_activity_service import (
    last_submission_map,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_invite_items_service import (
    build_invite_item,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateInviteListItem,
)
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import Task
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow


async def invite_list_for_principal(
    db: AsyncSession, principal: Principal, *, include_terminated: bool = False
) -> list[CandidateInviteListItem]:
    """Execute invite list for principal."""
    email = (principal.email or "").strip().lower()
    sessions = await cs_repo.list_for_email(
        db, email, include_terminated=include_terminated
    )
    items: list[CandidateInviteListItem] = []
    now = shared_utcnow()
    session_ids = [cs.id for cs in sessions]
    last_submitted_map = await last_submission_map(db, session_ids)
    completed_ids_map: dict[int, set[int]] = {}
    if session_ids and hasattr(db, "execute"):
        completed_ids_map = await cs_repo.completed_task_ids_bulk(db, session_ids)
    tasks_cache: dict[int, list[Task]] = {}
    invite_item_parameters = inspect.signature(build_invite_item).parameters
    supports_completed_ids = "completed_ids" in invite_item_parameters

    async def _tasks_for_trial(trial_id: int) -> list[Task]:
        if trial_id not in tasks_cache:
            tasks_cache[trial_id] = await cs_repo.tasks_for_trial(db, trial_id)
        return tasks_cache[trial_id]

    for cs in sessions:
        build_kwargs = {
            "now": now,
            "last_submitted_map": last_submitted_map,
            "tasks_loader": _tasks_for_trial,
        }
        if supports_completed_ids:
            build_kwargs["completed_ids"] = completed_ids_map.get(cs.id, set())
        items.append(
            await build_invite_item(
                db,
                cs,
                **build_kwargs,
            )
        )
    return items
