from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_missing_branch_sha_raises(
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
            return {}

        async def get_repo(self, _repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, _repo_full_name: str, _branch: str):
            return {"commit": {"sha": "   "}}

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: StubGithubClient(),
    )

    with pytest.raises(RuntimeError):
        await enforcement_handler.handle_day_close_enforcement(payload)

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is None
