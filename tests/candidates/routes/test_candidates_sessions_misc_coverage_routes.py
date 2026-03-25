from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.candidates.routes.candidate_sessions_routes import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_current_task_logic_routes as current_task_logic,
)
from app.candidates.routes.candidate_sessions_routes import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_schedule_routes as cs_schedule,
)


@pytest.mark.asyncio
async def test_schedule_route_returns_rendered_response(monkeypatch):
    candidate_session = SimpleNamespace(id=77)

    async def _schedule_candidate_session(*_args, **_kwargs):
        return SimpleNamespace(candidate_session=candidate_session)

    monkeypatch.setattr(
        cs_schedule.cs_service,
        "schedule_candidate_session",
        _schedule_candidate_session,
    )
    monkeypatch.setattr(
        cs_schedule,
        "render_schedule_response",
        lambda session: {"candidateSessionId": session.id},
    )
    response = await cs_schedule.schedule_candidate_session(
        token="t" * 24,
        payload=SimpleNamespace(
            scheduledStartAt=datetime.now(UTC), candidateTimezone="UTC"
        ),
        request=SimpleNamespace(headers={"x-correlation-id": "corr-123"}),
        principal=SimpleNamespace(sub="auth0|candidate"),
        db=object(),
        email_service=object(),
    )
    assert response["candidateSessionId"] == 77


@pytest.mark.asyncio
async def test_build_current_task_view_fetches_day_audit_when_incomplete(monkeypatch):
    request = SimpleNamespace(
        headers={"x-candidate-session-id": "5"},
        client=SimpleNamespace(host="127.0.0.1"),
    )
    current_task = SimpleNamespace(
        id=10, day_index=2, title="Task", type="code", description="desc"
    )
    candidate_session = SimpleNamespace(id=5, status="in_progress", completed_at=None)
    captured: dict[str, object] = {}

    async def _fetch_owned_session(_db, _session_id, _principal, now):
        return candidate_session

    async def _progress_snapshot(_db, _candidate_session, **_kwargs):
        return ([], set(), current_task, 0, 1, False)

    async def _get_day_audit(_db, *, candidate_session_id, day_index):
        captured["day_audit_called"] = (candidate_session_id, day_index)
        return SimpleNamespace(cutoff_commit_sha="sha", cutoff_at=None)

    monkeypatch.setattr(
        current_task_logic.cs_service, "fetch_owned_session", _fetch_owned_session
    )
    monkeypatch.setattr(
        current_task_logic.cs_service,
        "ensure_schedule_started_for_content",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        current_task_logic.cs_service, "progress_snapshot", _progress_snapshot
    )
    monkeypatch.setattr(current_task_logic.cs_repo, "get_day_audit", _get_day_audit)
    monkeypatch.setattr(
        current_task_logic,
        "build_current_task_response",
        lambda *_a, **kwargs: kwargs["day_audit"],
    )
    monkeypatch.setattr(
        current_task_logic.rate_limit, "rate_limit_enabled", lambda: False
    )
    day_audit = await current_task_logic.build_current_task_view(
        5, request, SimpleNamespace(sub="auth0|candidate"), object()
    )
    assert captured["day_audit_called"] == (5, 2)
    assert day_audit.cutoff_commit_sha == "sha"
