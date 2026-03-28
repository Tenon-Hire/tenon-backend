from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_group_target_dedupes_same_repo(async_session):
    recruiter = await create_recruiter(
        async_session,
        email=f"workspace-cleanup-group-dedupe-{uuid4().hex}@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="completed",
        with_default_schedule=True,
    )
    created_at = datetime.now(UTC) - timedelta(days=60)
    await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/shared-repo",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="other",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/shared-repo",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    await async_session.commit()

    targets = await cleanup_handler._list_company_cleanup_targets(
        async_session,
        company_id=simulation.company_id,
    )
    assert len(targets) == 1
