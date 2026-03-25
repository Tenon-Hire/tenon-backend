from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_run_task_tests_github_error(monkeypatch, async_session):
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
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "validate_branch",
        lambda branch: branch,
    )

    class Runner:
        async def dispatch_and_wait(self, **_kwargs):
            raise GithubError("nope")

    with pytest.raises(HTTPException) as excinfo:
        await candidate_submissions.run_task_tests(
            task_id=task.id,
            payload=RunTestsRequest(branch="main", workflowInputs=None),
            db=async_session,
            actions_runner=Runner(),
            candidate_session=cs,
        )
    assert excinfo.value.status_code == 502
