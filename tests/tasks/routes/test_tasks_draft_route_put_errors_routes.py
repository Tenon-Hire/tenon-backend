from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from app.submissions.schemas.submissions_schemas_submissions_task_drafts_schema import (
    TaskDraftUpsertRequest,
)
from app.tasks.routes.tasks import tasks_routes_tasks_tasks_draft_routes as draft_route


@pytest.mark.asyncio
async def test_put_task_draft_route_duplicate_submission_returns_finalized(monkeypatch):
    candidate_session = SimpleNamespace(id=10, trial_id=20)
    task = SimpleNamespace(id=33, trial_id=20)

    async def _load_task(_db, _task_id):
        return task

    async def _find_duplicate(_db, _candidate_session_id, _task_id):
        return True

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
    with pytest.raises(ApiError) as excinfo:
        await draft_route.put_task_draft_route(
            task_id=33,
            payload=TaskDraftUpsertRequest(contentText="x", contentJson={"a": 1}),
            candidate_session=candidate_session,
            db=object(),
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "DRAFT_FINALIZED"


@pytest.mark.asyncio
async def test_put_task_draft_route_finalized_draft_error(monkeypatch):
    candidate_session = SimpleNamespace(id=10, trial_id=20)
    task = SimpleNamespace(id=33, trial_id=20)

    async def _load_task(_db, _task_id):
        return task

    async def _find_duplicate(_db, _candidate_session_id, _task_id):
        return False

    async def _upsert(*_args, **_kwargs):
        raise task_drafts_repo.TaskDraftFinalizedError()

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
        draft_route, "validate_draft_payload_size", lambda **_kwargs: (1, 1)
    )
    monkeypatch.setattr(task_drafts_repo, "upsert_draft", _upsert)
    with pytest.raises(ApiError) as excinfo:
        await draft_route.put_task_draft_route(
            task_id=33,
            payload=TaskDraftUpsertRequest(contentText="x", contentJson={"a": 1}),
            candidate_session=candidate_session,
            db=object(),
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "DRAFT_FINALIZED"
