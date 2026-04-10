from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_persists_cutoff_and_revokes_collaborator(
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
        def __init__(self):
            self.calls: list[tuple[str, str, str]] = []

        async def remove_collaborator(self, repo_full_name: str, username: str):
            self.calls.append(("remove_collaborator", repo_full_name, username))
            return {}

        async def get_repo(self, repo_full_name: str):
            self.calls.append(("get_repo", repo_full_name, ""))
            return {"default_branch": "main"}

        async def get_branch(self, repo_full_name: str, branch: str):
            self.calls.append(("get_branch", repo_full_name, branch))
            return {"commit": {"sha": "cutoff-sha-123"}}

    client = StubGithubClient()
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(enforcement_handler, "get_github_client", lambda: client)

    result = await enforcement_handler.handle_day_close_enforcement(payload)

    assert result["status"] == "cutoff_persisted"
    assert result["candidateSessionId"] == candidate_session.id
    assert result["taskId"] == day2_task.id
    assert result["dayIndex"] == 2
    assert result["cutoffCommitSha"] == "cutoff-sha-123"
    assert result["cutoffAt"] == cutoff_at.isoformat().replace("+00:00", "Z")
    assert result["evalBasisRef"] == "refs/heads/main@cutoff"
    assert result["revokeStatus"] == "collaborator_removed"
    assert client.calls == [
        ("remove_collaborator", "org/candidate-repo", "octocat"),
        ("get_branch", "org/candidate-repo", "main"),
    ]

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is not None
    assert day_audit.cutoff_commit_sha == "cutoff-sha-123"
    observed_cutoff_at = day_audit.cutoff_at
    if observed_cutoff_at.tzinfo is None:
        observed_cutoff_at = observed_cutoff_at.replace(tzinfo=UTC)
    assert observed_cutoff_at == cutoff_at
    assert day_audit.eval_basis_ref == "refs/heads/main@cutoff"
