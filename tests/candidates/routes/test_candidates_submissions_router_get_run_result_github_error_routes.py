from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_get_run_result_github_error(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    workspace = _stub_workspace()
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "load_task_or_404",
        _async_return(task),
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "ensure_task_belongs",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "validate_run_allowed",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.workspace_repo,
        "get_by_session_and_task",
        _async_return(workspace),
    )

    class Runner:
        async def fetch_run_result(self, **_kw):
            raise GithubError("fail")

    with pytest.raises(HTTPException) as excinfo:
        await candidate_submissions.get_run_result(
            task_id=task.id,
            run_id=123,
            db=async_session,
            actions_runner=Runner(),
            candidate_session=cs,
        )
    assert excinfo.value.status_code == 502
