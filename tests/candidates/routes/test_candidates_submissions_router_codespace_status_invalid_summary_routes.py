from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_codespace_status_invalid_summary(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    workspace = _stub_workspace()
    workspace.last_test_summary_json = "{not-json"
    workspace.codespace_url = "https://codespaces.new/org/repo?quickstart=1"
    workspace.precommit_sha = "precommit-sha-2"

    async def _return_task(*_a, **_k):
        return task

    async def _return_workspace_obj(*_a, **_kw):
        return workspace

    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "load_task_or_404",
        _return_task,
    )
    monkeypatch.setattr(
        candidate_submissions.workspace_repo,
        "get_by_session_and_task",
        _return_workspace_obj,
    )

    resp = await candidate_submissions.codespace_status(
        task_id=task.id,
        candidate_session=cs,
        db=async_session,
        github_client=object(),
    )
    assert resp.lastTestSummary is None
    assert resp.repoFullName == workspace.repo_full_name
    assert resp.codespaceUrl == "https://codespaces.new/org/repo?quickstart=1"
    assert not hasattr(resp, "baseTemplateSha")
    assert not hasattr(resp, "precommitSha")
