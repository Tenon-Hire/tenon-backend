from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_repo_state_service as repo_state_service,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_run_tests_service as run_tests_service,
)


@pytest.mark.asyncio
async def test_run_task_tests_unarchives_archived_repo_before_dispatch(monkeypatch):
    task = SimpleNamespace(id=2, type="code")
    candidate_session = SimpleNamespace(id=11)
    workspace = SimpleNamespace(
        repo_full_name="winoe-ai-repos/winoe-ws-123",
        default_branch="main",
    )
    calls: list[str] = []

    class StubGithubClient:
        async def get_repo(self, repo_full_name: str):
            calls.append(f"get:{repo_full_name}")
            return {"full_name": repo_full_name, "archived": True}

        async def unarchive_repo(self, repo_full_name: str):
            calls.append(f"unarchive:{repo_full_name}")
            return {"full_name": repo_full_name, "archived": False}

    async def _load_task_or_404(_db, task_id: int):
        assert task_id == task.id
        return task

    def _ensure_task_belongs(_task, _candidate_session):
        return None

    def _validate_run_allowed(_task):
        return None

    @asynccontextmanager
    async def _concurrency_guard(*_args, **_kwargs):
        yield

    async def _get_workspace_by_session_and_task(*_args, **_kwargs):
        return workspace

    async def _ensure_day_flow_open(*_args, **_kwargs):
        return None

    async def _run_actions_tests(**_kwargs):
        calls.append("dispatch")
        return SimpleNamespace(run_id=9)

    async def _ensure_repo_is_active(github_client, repo_full_name: str):
        calls.append("active-check")
        assert isinstance(github_client, StubGithubClient)
        assert repo_full_name == workspace.repo_full_name
        return await repo_state_service.ensure_repo_is_active(
            github_client, repo_full_name
        )

    monkeypatch.setattr(
        run_tests_service.submission_service,
        "load_task_or_404",
        _load_task_or_404,
    )
    monkeypatch.setattr(
        run_tests_service.submission_service,
        "ensure_task_belongs",
        _ensure_task_belongs,
    )
    monkeypatch.setattr(
        run_tests_service.submission_service,
        "validate_run_allowed",
        _validate_run_allowed,
    )
    monkeypatch.setattr(
        run_tests_service.submission_service.workspace_repo,
        "get_by_session_and_task",
        _get_workspace_by_session_and_task,
    )
    monkeypatch.setattr(
        run_tests_service.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        run_tests_service, "ensure_day_flow_open", _ensure_day_flow_open
    )
    monkeypatch.setattr(run_tests_service, "concurrency_guard", _concurrency_guard)
    monkeypatch.setattr(
        run_tests_service.submission_service,
        "run_actions_tests",
        _run_actions_tests,
    )
    monkeypatch.setattr(
        run_tests_service, "ensure_repo_is_active", _ensure_repo_is_active
    )
    monkeypatch.setattr(
        run_tests_service, "apply_rate_limit", lambda *_args, **_kwargs: None
    )

    (
        task_result,
        workspace_result,
        actions_result,
    ) = await run_tests_service.run_task_tests(
        db=object(),
        candidate_session=candidate_session,
        task_id=task.id,
        runner=SimpleNamespace(client=StubGithubClient()),
        branch=None,
        workflow_inputs=None,
    )

    assert task_result is task
    assert workspace_result is workspace
    assert actions_result.run_id == 9
    assert calls == [
        "active-check",
        f"get:{workspace.repo_full_name}",
        f"unarchive:{workspace.repo_full_name}",
        "dispatch",
    ]
