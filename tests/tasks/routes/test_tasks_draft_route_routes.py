from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from app.tasks.routes.tasks import tasks_routes_tasks_tasks_draft_routes as draft_route


@pytest.mark.asyncio
async def test_get_task_draft_route_success(monkeypatch):
    candidate_session = SimpleNamespace(id=10, trial_id=20)
    task = SimpleNamespace(id=33, trial_id=20)
    draft = SimpleNamespace(
        content_text="hello",
        content_json={"a": 1},
        updated_at=datetime.now(UTC),
        finalized_at=None,
        finalized_submission_id=None,
    )

    async def _load_task(_db, _task_id):
        return task

    async def _get_draft(_db, *, candidate_session_id: int, task_id: int):
        assert candidate_session_id == 10 and task_id == 33
        return draft

    monkeypatch.setattr(draft_route.submission_service, "load_task_or_404", _load_task)
    monkeypatch.setattr(
        draft_route.submission_service, "ensure_task_belongs", lambda *_a, **_k: None
    )
    monkeypatch.setattr(task_drafts_repo, "get_by_session_and_task", _get_draft)
    response = await draft_route.get_task_draft_route(
        task_id=33, candidate_session=candidate_session, db=object()
    )
    assert response.taskId == 33
    assert response.contentText == "hello"
    assert response.contentJson == {"a": 1}


@pytest.mark.asyncio
async def test_get_task_draft_route_not_found(monkeypatch):
    candidate_session = SimpleNamespace(id=10, trial_id=20)
    task = SimpleNamespace(id=33, trial_id=20)

    async def _load_task(_db, _task_id):
        return task

    async def _get_draft(_db, **_kwargs):
        return None

    monkeypatch.setattr(draft_route.submission_service, "load_task_or_404", _load_task)
    monkeypatch.setattr(
        draft_route.submission_service, "ensure_task_belongs", lambda *_a, **_k: None
    )
    monkeypatch.setattr(task_drafts_repo, "get_by_session_and_task", _get_draft)
    with pytest.raises(ApiError) as excinfo:
        await draft_route.get_task_draft_route(
            task_id=33, candidate_session=candidate_session, db=object()
        )
    assert excinfo.value.status_code == 404
    assert excinfo.value.error_code == "DRAFT_NOT_FOUND"
