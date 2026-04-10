from __future__ import annotations

# helper import baseline for restructure-compat
import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
)
from app.evaluations.repositories import (
    repository as evaluation_repo,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_jobs_service import (
    EVALUATION_RUN_JOB_TYPE,
)
from app.shared.database.shared_database_models_model import Submission, Task
from app.shared.jobs import worker
from app.shared.jobs.handlers.shared_jobs_handlers_evaluation_run_handler import (
    handle_evaluation_run,
)
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    Job,
)
from app.submissions.repositories.submissions_repositories_submissions_winoe_report_model import (
    WinoeReport,
)
from tests.evaluations.routes.evaluations_winoe_report_seed_artifact_utils import (
    _seed_cutoff_day_audits,
    _seed_handoff_and_reflection,
)
from tests.evaluations.routes.evaluations_winoe_report_seed_base_utils import (
    _seed_day1_day2_day3_submissions,
    _seed_winoe_report_candidate_session,
)
from tests.shared.factories import create_talent_partner


class _SharedSessionContext:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _SharedSessionMaker:
    def __init__(self, session: AsyncSession):
        self._session = session

    def __call__(self) -> _SharedSessionContext:
        return _SharedSessionContext(self._session)


async def _seed_completed_candidate_session(
    async_session: AsyncSession,
    *,
    ai_eval_enabled_by_day: dict[str, bool] | None = None,
):
    (
        talent_partner,
        candidate_session,
        tasks_by_day,
    ) = await _seed_winoe_report_candidate_session(
        async_session,
        ai_eval_enabled_by_day=ai_eval_enabled_by_day,
    )
    await _seed_day1_day2_day3_submissions(
        async_session,
        candidate_session=candidate_session,
        tasks_by_day=tasks_by_day,
    )
    await _seed_handoff_and_reflection(
        async_session,
        candidate_session=candidate_session,
        tasks_by_day=tasks_by_day,
    )
    await _seed_cutoff_day_audits(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    await async_session.commit()
    return talent_partner, candidate_session


async def _run_worker_once(async_session: AsyncSession, *, worker_id: str) -> bool:
    session_maker = _SharedSessionMaker(async_session)
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled_any = False
        for iteration in range(16):
            handled = await worker.run_once(
                session_maker=session_maker,
                worker_id=f"{worker_id}-{iteration}",
                now=datetime.now(UTC),
            )
            # Let async DB connection cleanup tasks settle before the next worker pass.
            await asyncio.sleep(0)
            if not handled:
                return handled_any
            handled_any = True
        raise AssertionError(
            "worker test helper exceeded 16 iterations while draining queued jobs"
        )
    finally:
        worker.clear_handlers()


__all__ = [name for name in globals() if not name.startswith("__")]
