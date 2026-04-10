from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from app.submissions.schemas.submissions_schemas_submissions_task_drafts_schema import (
    TaskDraftUpsertRequest,
)
from app.tasks.routes.tasks import tasks_routes_tasks_tasks_draft_routes as draft_route


@pytest.mark.asyncio
async def test_put_task_draft_route_success(monkeypatch):
    candidate_session = SimpleNamespace(id=10, trial_id=20)
    task = SimpleNamespace(id=33, trial_id=20)
    draft = SimpleNamespace(updated_at=datetime.now(UTC))

    async def _load_task(_db, _task_id):
        return task

    async def _find_duplicate(_db, _candidate_session_id, _task_id):
        return False

    async def _upsert(_db, **kwargs):
        assert kwargs["candidate_session_id"] == 10
        assert kwargs["task_id"] == 33
        assert kwargs["content_text"] == "x"
        assert kwargs["content_json"] == {"a": 1}
        return draft

    monkeypatch.setattr(draft_route.submission_service, "load_task_or_404", _load_task)
    monkeypatch.setattr(
        draft_route.submission_service, "ensure_task_belongs", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        draft_route.cs_service, "require_active_window", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        draft_route.submission_service.submissions_repo,
        "find_duplicate",
        _find_duplicate,
    )
    monkeypatch.setattr(
        draft_route, "validate_draft_payload_size", lambda **_kwargs: (3, 7)
    )
    monkeypatch.setattr(task_drafts_repo, "upsert_draft", _upsert)
    response = await draft_route.put_task_draft_route(
        task_id=33,
        payload=TaskDraftUpsertRequest(contentText="x", contentJson={"a": 1}),
        candidate_session=candidate_session,
        db=object(),
    )
    assert response.taskId == 33
    assert response.updatedAt == draft.updated_at
