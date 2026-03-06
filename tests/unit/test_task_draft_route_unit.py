from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.api.routers.tasks import draft as draft_route
from app.core.errors import ApiError
from app.repositories.task_drafts import repository as task_drafts_repo
from app.schemas.task_drafts import TaskDraftUpsertRequest


@pytest.mark.asyncio
async def test_get_task_draft_route_success(monkeypatch):
    candidate_session = SimpleNamespace(id=10, simulation_id=20)
    task = SimpleNamespace(id=33, simulation_id=20)
    draft = SimpleNamespace(
        content_text="hello",
        content_json={"a": 1},
        updated_at=datetime.now(UTC),
        finalized_at=None,
        finalized_submission_id=None,
    )

    async def _load_task(_db, _task_id):
        return task

    def _ensure_task_belongs(_task, _candidate_session):
        return None

    async def _get_draft(_db, *, candidate_session_id: int, task_id: int):
        assert candidate_session_id == 10
        assert task_id == 33
        return draft

    monkeypatch.setattr(draft_route.submission_service, "load_task_or_404", _load_task)
    monkeypatch.setattr(
        draft_route.submission_service,
        "ensure_task_belongs",
        _ensure_task_belongs,
    )
    monkeypatch.setattr(task_drafts_repo, "get_by_session_and_task", _get_draft)

    response = await draft_route.get_task_draft_route(
        task_id=33,
        candidate_session=candidate_session,
        db=object(),
    )
    assert response.taskId == 33
    assert response.contentText == "hello"
    assert response.contentJson == {"a": 1}


@pytest.mark.asyncio
async def test_get_task_draft_route_not_found(monkeypatch):
    candidate_session = SimpleNamespace(id=10, simulation_id=20)
    task = SimpleNamespace(id=33, simulation_id=20)

    async def _load_task(_db, _task_id):
        return task

    async def _get_draft(_db, **_kwargs):
        return None

    monkeypatch.setattr(draft_route.submission_service, "load_task_or_404", _load_task)
    monkeypatch.setattr(
        draft_route.submission_service,
        "ensure_task_belongs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(task_drafts_repo, "get_by_session_and_task", _get_draft)

    with pytest.raises(ApiError) as excinfo:
        await draft_route.get_task_draft_route(
            task_id=33,
            candidate_session=candidate_session,
            db=object(),
        )
    assert excinfo.value.status_code == 404
    assert excinfo.value.error_code == "DRAFT_NOT_FOUND"


@pytest.mark.asyncio
async def test_put_task_draft_route_duplicate_submission_returns_finalized(monkeypatch):
    candidate_session = SimpleNamespace(id=10, simulation_id=20)
    task = SimpleNamespace(id=33, simulation_id=20)

    async def _load_task(_db, _task_id):
        return task

    async def _find_duplicate(_db, _candidate_session_id, _task_id):
        return True

    monkeypatch.setattr(draft_route.submission_service, "load_task_or_404", _load_task)
    monkeypatch.setattr(
        draft_route.submission_service,
        "ensure_task_belongs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        draft_route.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
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
    candidate_session = SimpleNamespace(id=10, simulation_id=20)
    task = SimpleNamespace(id=33, simulation_id=20)

    async def _load_task(_db, _task_id):
        return task

    async def _find_duplicate(_db, _candidate_session_id, _task_id):
        return False

    async def _upsert(*_args, **_kwargs):
        raise task_drafts_repo.TaskDraftFinalizedError()

    monkeypatch.setattr(draft_route.submission_service, "load_task_or_404", _load_task)
    monkeypatch.setattr(
        draft_route.submission_service,
        "ensure_task_belongs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        draft_route.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        draft_route.submission_service.submissions_repo,
        "find_duplicate",
        _find_duplicate,
    )
    monkeypatch.setattr(
        draft_route,
        "validate_draft_payload_size",
        lambda **_kwargs: (1, 1),
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


@pytest.mark.asyncio
async def test_put_task_draft_route_success(monkeypatch):
    candidate_session = SimpleNamespace(id=10, simulation_id=20)
    task = SimpleNamespace(id=33, simulation_id=20)
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
        draft_route.submission_service,
        "ensure_task_belongs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        draft_route.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        draft_route.submission_service.submissions_repo,
        "find_duplicate",
        _find_duplicate,
    )
    monkeypatch.setattr(
        draft_route,
        "validate_draft_payload_size",
        lambda **_kwargs: (3, 7),
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
