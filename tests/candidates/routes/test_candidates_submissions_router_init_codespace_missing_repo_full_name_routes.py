from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_init_codespace_missing_repo_full_name(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    workspace = _stub_workspace()
    workspace.repo_full_name = ""

    async def _return_task(*_a, **_k):
        return task

    async def _return_workspace(*_a, **_k):
        return workspace

    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "load_task_or_404",
        _return_task,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "ensure_task_belongs",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "ensure_in_order",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "validate_run_allowed",
        lambda *a, **k: None,
    )

    async def _return_snapshot(*_a, **_k):
        return ([], set(), task, 0, 1, False)

    monkeypatch.setattr(
        candidate_submissions.cs_service, "progress_snapshot", _return_snapshot
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "ensure_workspace",
        _return_workspace,
    )

    payload = CodespaceInitRequest(githubUsername="octocat")
    with pytest.raises(HTTPException) as excinfo:
        await candidate_submissions.init_codespace(
            task_id=task.id,
            payload=payload,
            candidate_session=cs,
            db=async_session,
            github_client=object(),
        )
    assert excinfo.value.status_code == 409
