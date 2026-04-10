from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_uses_group_as_canonical_and_skips_duplicate_legacy(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session,
        email=f"workspace-cleanup-canonical-{uuid4().hex}@test.com",
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
        with_default_schedule=True,
    )

    created_at = datetime.now(UTC) - timedelta(days=60)
    group = await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/shared-repo",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )

    day2_task = next(task for task in tasks if task.day_index == 2)
    day3_task = next(task for task in tasks if task.day_index == 3)

    await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=group.id,
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        template_repo_full_name=group.template_repo_full_name,
        repo_full_name=group.repo_full_name,
        repo_id=999,
        default_branch=group.default_branch,
        base_template_sha=group.base_template_sha,
        created_at=created_at,
    )
    legacy = await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=None,
        candidate_session_id=candidate_session.id,
        task_id=day3_task.id,
        template_repo_full_name="org/template-repo",
        repo_full_name="org/shared-repo",
        repo_id=1000,
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    await async_session.commit()

    class StubGithubClient:
        def __init__(self):
            self.archive_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            self.archive_calls += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    github_client = StubGithubClient()
    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(cleanup_handler, "get_github_client", lambda: github_client)

    result = await cleanup_handler.handle_workspace_cleanup(
        {"companyId": trial.company_id}
    )

    await async_session.refresh(group)
    await async_session.refresh(legacy)
    group_stored = group
    legacy_stored = legacy

    assert result["archived"] == 1
    assert result["candidateCount"] == 1
    assert github_client.archive_calls == 1
    assert group_stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert legacy_stored.cleanup_status is None
