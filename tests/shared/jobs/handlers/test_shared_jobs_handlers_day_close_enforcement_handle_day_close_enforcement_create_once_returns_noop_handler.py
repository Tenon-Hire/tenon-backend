from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_create_once_returns_noop(
    async_session,
    monkeypatch,
):
    (
        _trial,
        candidate_session,
        day2_task,
        cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)

    class StubGithubClient:
        async def remove_collaborator(self, _repo_full_name: str, _username: str):
            return {}

        async def get_repo(self, _repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, _repo_full_name: str, _branch: str):
            return {"commit": {"sha": "race-sha"}}

    async def _fake_create_day_audit_once(*_args, **_kwargs):
        return (
            SimpleNamespace(
                cutoff_commit_sha="persisted-sha",
                cutoff_at=cutoff_at,
                eval_basis_ref="refs/heads/main@cutoff",
            ),
            False,
        )

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: StubGithubClient(),
    )
    monkeypatch.setattr(
        enforcement_handler.cs_repo,
        "create_day_audit_once",
        _fake_create_day_audit_once,
    )

    result = await enforcement_handler.handle_day_close_enforcement(payload)
    assert result["status"] == "no_op_cutoff_exists"
    assert result["candidateSessionId"] == candidate_session.id
    assert result["taskId"] == day2_task.id
    assert result["dayIndex"] == 2
    assert result["cutoffCommitSha"] == "persisted-sha"
    assert result["evalBasisRef"] == "refs/heads/main@cutoff"
