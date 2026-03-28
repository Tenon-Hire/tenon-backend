from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_init_codespace_maps_github_error(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()

    async def _return_task(*_a, **_k):
        return task

    async def _return_current(*_a, **_k):
        return task

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

    async def _raise_workspace(*_a, **_kw):
        raise GithubError("boom")

    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "ensure_workspace",
        _raise_workspace,
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
    assert excinfo.value.status_code == 502
