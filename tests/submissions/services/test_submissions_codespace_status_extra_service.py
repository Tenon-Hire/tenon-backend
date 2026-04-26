from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    WorkspaceMissing,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_codespace_status_service as status_service,
)


@pytest.mark.asyncio
async def test_codespace_status_ignores_invalid_test_summary_and_requires_repo(
    monkeypatch,
):
    candidate_session = SimpleNamespace(id=1)
    task = SimpleNamespace(id=2)
    workspace = SimpleNamespace(
        repo_full_name="",
        last_test_summary_json="{not-json",
    )

    monkeypatch.setattr(
        status_service.submission_service,
        "load_task_or_404",
        lambda *_args, **_kwargs: task,
    )

    async def _load_task(*_args, **_kwargs):
        return task

    async def _load_workspace(*_args, **_kwargs):
        return workspace

    monkeypatch.setattr(
        status_service.submission_service, "load_task_or_404", _load_task
    )
    monkeypatch.setattr(
        status_service.submission_service,
        "ensure_task_belongs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        status_service.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        status_service.submission_service.workspace_repo,
        "get_by_session_and_task",
        _load_workspace,
    )
    monkeypatch.setattr(status_service, "ensure_day_flow_open", _load_task)

    with pytest.raises(WorkspaceMissing):
        await status_service.codespace_status(
            "db", candidate_session=candidate_session, task_id=task.id
        )
