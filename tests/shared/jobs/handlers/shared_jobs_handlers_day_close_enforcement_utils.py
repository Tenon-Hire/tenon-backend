from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_constants import (
    day_close_enforcement_idempotency_key,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_service import (
    build_day_close_enforcement_payload,
)
from app.integrations.github import GithubError
from app.shared.jobs import worker
from app.shared.jobs.handlers import (
    DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
)
from app.shared.jobs.handlers import (
    day_close_enforcement as enforcement_handler,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
)
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.fixture(autouse=True)
def _clear_job_handlers():
    worker.clear_handlers()
    yield
    worker.clear_handlers()


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )


async def _prepare_code_day_context(async_session: AsyncSession):
    talent_partner = await create_talent_partner(
        async_session, email="cutoff-enforcement-handler@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        with_default_schedule=True,
    )
    candidate_session.github_username = "octocat"
    day2_task = next(task for task in tasks if task.day_index == 2)
    now = datetime.now(UTC).replace(microsecond=0)

    group = await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/candidate-repo",
        default_branch="main",
        base_template_sha="template-base-sha",
        created_at=now,
    )
    await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=group.id,
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        template_repo_full_name=group.template_repo_full_name,
        repo_full_name=group.repo_full_name,
        repo_id=12345,
        default_branch=group.default_branch,
        base_template_sha=group.base_template_sha,
        created_at=now,
    )
    await async_session.commit()

    cutoff_at = now + timedelta(hours=1)
    payload = build_day_close_enforcement_payload(
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        day_index=day2_task.day_index,
        window_end_at=cutoff_at,
    )
    return trial, candidate_session, day2_task, cutoff_at, payload


__all__ = [name for name in globals() if not name.startswith("__")]
