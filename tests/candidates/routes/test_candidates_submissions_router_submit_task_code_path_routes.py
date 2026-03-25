from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_submit_task_code_path(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    workspace = _stub_workspace()
    service = candidate_submissions.submission_service
    result = ActionsRunResult(
        status="passed",
        run_id=11,
        conclusion="success",
        passed=1,
        failed=0,
        total=1,
        stdout="ok",
        stderr=None,
        head_sha="sha",
        html_url="https://example.com",
        raw=None,
    )
    monkeypatch.setattr(
        candidate_submissions, "_rate_limit_or_429", lambda *_a, **_k: None
    )

    async def _return_snapshot(*_a, **_k):
        return ([], set(), task, 0, 1, False)

    monkeypatch.setattr(
        candidate_submissions.cs_service, "progress_snapshot", _return_snapshot
    )
    monkeypatch.setattr(service, "load_task_or_404", _async_return(task))
    monkeypatch.setattr(service, "ensure_task_belongs", lambda *a, **k: None)
    monkeypatch.setattr(service, "ensure_not_duplicate", _async_return(None))
    monkeypatch.setattr(service, "ensure_in_order", lambda *a, **k: None)
    monkeypatch.setattr(service, "validate_submission_payload", lambda *a, **k: None)
    monkeypatch.setattr(
        service,
        "workspace_repo",
        SimpleNamespace(get_by_session_and_task=_async_return(workspace)),
    )
    monkeypatch.setattr(service, "validate_branch", lambda branch: branch)
    monkeypatch.setattr(service, "run_actions_tests", _async_return(result))
    monkeypatch.setattr(service, "record_run_result", _async_return(workspace))

    class StubGithubClient:
        async def get_compare(self, repo_full_name, base, head):
            return {"files": []}

    async def fake_create_submission(db, candidate_session, task, payload, **_kw):
        return SimpleNamespace(
            id=99,
            task_id=task.id,
            candidate_session_id=candidate_session.id,
            submitted_at=datetime.now(UTC),
        )

    monkeypatch.setattr(service, "create_submission", fake_create_submission)
    monkeypatch.setattr(
        service, "progress_after_submission", _async_return((1, 5, False))
    )

    resp = await candidate_submissions.submit_task(
        task_id=task.id,
        payload=SubmissionCreateRequest(contentText=None),
        candidate_session=cs,
        db=async_session,
        github_client=StubGithubClient(),
        actions_runner=object(),
    )
    assert resp.submissionId == 99
    assert resp.progress.completed == 1
