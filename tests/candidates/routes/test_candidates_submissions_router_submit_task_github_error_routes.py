from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_submit_task_github_error(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    workspace = _stub_workspace()

    async def _return_snapshot(*_a, **_k):
        return ([], set(), task, 0, 1, False)

    monkeypatch.setattr(
        candidate_submissions.cs_service, "progress_snapshot", _return_snapshot
    )
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
        "ensure_not_duplicate",
        _async_return(None),
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "ensure_in_order",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "validate_submission_payload",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "is_code_task",
        lambda _task: True,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "workspace_repo",
        SimpleNamespace(get_by_session_and_task=_async_return(workspace)),
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "validate_branch",
        lambda branch: branch,
    )

    class Runner:
        async def dispatch_and_wait(self, **_kw):
            raise GithubError("fail")

    with pytest.raises(HTTPException) as excinfo:
        await candidate_submissions.submit_task(
            task_id=task.id,
            payload=SubmissionCreateRequest(contentText=None),
            candidate_session=cs,
            db=async_session,
            github_client=object(),
            actions_runner=Runner(),
        )
    assert excinfo.value.status_code == 502
