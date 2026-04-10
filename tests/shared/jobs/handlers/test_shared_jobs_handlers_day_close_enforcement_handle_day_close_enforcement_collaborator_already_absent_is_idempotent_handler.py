from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_collaborator_already_absent_is_idempotent(
    async_session,
    monkeypatch,
):
    (
        _trial,
        candidate_session,
        _day2_task,
        _cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)

    class StubGithubClient:
        async def remove_collaborator(self, _repo_full_name: str, _username: str):
            raise GithubError("not found", status_code=404)

        async def get_repo(self, _repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, _repo_full_name: str, _branch: str):
            return {"commit": {"sha": "cutoff-sha-idempotent"}}

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: StubGithubClient(),
    )

    result = await enforcement_handler.handle_day_close_enforcement(payload)

    assert result["status"] == "cutoff_persisted"
    assert result["revokeStatus"] == "collaborator_not_found"
    assert result["cutoffCommitSha"] == "cutoff-sha-idempotent"

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is not None
    assert day_audit.cutoff_commit_sha == "cutoff-sha-idempotent"
