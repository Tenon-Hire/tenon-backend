from __future__ import annotations

import builtins
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_constants import (
    day_close_finalize_text_idempotency_key,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_payloads_service import (
    build_day_close_finalize_text_payload,
)
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    serialize_day_windows,
)
from app.shared.database.shared_database_models_model import Submission
from app.shared.jobs.handlers import (
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
)
from app.shared.jobs.handlers import (
    day_close_finalize_text as finalize_handler,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_SUCCEEDED,
)
from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from app.submissions.services.task_drafts import NO_DRAFT_AT_CUTOFF_MARKER
from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
    create_trial,
)


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )


async def _set_fully_closed_schedule(
    async_session, *, candidate_session
) -> dict[int, datetime]:
    now_utc = datetime.now(UTC).replace(microsecond=0)
    day_windows: list[dict[str, object]] = []
    window_end_by_day: dict[int, datetime] = {}
    for day_index in range(1, 6):
        window_end = now_utc - timedelta(days=6 - day_index)
        window_start = window_end - timedelta(hours=8)
        day_windows.append(
            {
                "dayIndex": day_index,
                "windowStartAt": window_start,
                "windowEndAt": window_end,
            }
        )
        window_end_by_day[day_index] = window_end

    candidate_session.scheduled_start_at = day_windows[0]["windowStartAt"]
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()
    return window_end_by_day


def _payload(
    *,
    candidate_session_id: int,
    task_id: int,
    day_index: int,
    window_end_at: datetime,
) -> dict[str, object]:
    return {
        "candidateSessionId": candidate_session_id,
        "taskId": task_id,
        "dayIndex": day_index,
        "windowEndAt": window_end_at.isoformat().replace("+00:00", "Z"),
    }


__all__ = [name for name in globals() if not name.startswith("__")]
