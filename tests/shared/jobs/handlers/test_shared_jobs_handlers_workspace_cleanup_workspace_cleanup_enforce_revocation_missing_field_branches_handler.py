from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_enforce_revocation_missing_field_branches(
    async_session,
):
    created_at = datetime.now(UTC) - timedelta(days=30)
    (
        _company_id,
        candidate_session_id,
        _workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        with_cutoff=True,
        use_group=True,
    )

    record = (
        await async_session.execute(
            select(WorkspaceGroup).where(WorkspaceGroup.id == workspace_group_id)
        )
    ).scalar_one()
    candidate_session = (
        await async_session.execute(
            select(cleanup_handler.CandidateSession).where(
                cleanup_handler.CandidateSession.id == candidate_session_id
            )
        )
    ).scalar_one()
    now = datetime.now(UTC)

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

    record.repo_full_name = "   "
    missing_repo = await cleanup_handler._enforce_collaborator_revocation(
        StubGithubClient(),
        record=record,
        candidate_session=candidate_session,
        should_revoke=True,
        now=now,
        job_id="job-1",
    )
    assert missing_repo == "missing_repo"
    assert record.access_revocation_error == "missing_repo_full_name"

    record.repo_full_name = "org/real-repo"
    candidate_session.github_username = ""
    missing_username = await cleanup_handler._enforce_collaborator_revocation(
        StubGithubClient(),
        record=record,
        candidate_session=candidate_session,
        should_revoke=True,
        now=now,
        job_id="job-2",
    )
    assert missing_username == "missing_github_username"
    assert record.access_revocation_error == "missing_github_username"
