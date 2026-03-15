from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api import middleware_perf
from app.api.routers.admin_routes import demo_ops
from app.api.routers.candidate_sessions_routes import current_task_logic
from app.api.routers.candidate_sessions_routes import responses as cs_responses
from app.api.routers.candidate_sessions_routes import schedule as cs_schedule
from app.services import admin_ops_service
from app.services.task_drafts import finalization


@pytest.mark.asyncio
async def test_admin_demo_route_response_mapping(monkeypatch):
    monkeypatch.setattr(
        demo_ops.admin_ops_service,
        "reset_candidate_session",
        AsyncMock(
            return_value=admin_ops_service.CandidateSessionResetResult(
                candidate_session_id=101,
                reset_to="claimed",
                status="ok",
                audit_id="adm_reset",
            )
        ),
    )
    monkeypatch.setattr(
        demo_ops.admin_ops_service,
        "requeue_job",
        AsyncMock(
            return_value=admin_ops_service.JobRequeueResult(
                job_id="job-101",
                previous_status="dead_letter",
                new_status="queued",
                audit_id="adm_requeue",
            )
        ),
    )
    monkeypatch.setattr(
        demo_ops.admin_ops_service,
        "use_simulation_fallback_scenario",
        AsyncMock(
            return_value=admin_ops_service.SimulationFallbackResult(
                simulation_id=44,
                active_scenario_version_id=9,
                apply_to="future_invites_only",
                audit_id="adm_fallback",
            )
        ),
    )

    reset_response = await demo_ops.reset_candidate_session(
        candidate_session_id=101,
        payload=SimpleNamespace(
            targetState="claimed",
            reason="reset",
            overrideIfEvaluated=False,
            dryRun=False,
        ),
        db=object(),
        actor=SimpleNamespace(actor_id="actor-1"),
    )
    assert reset_response.candidateSessionId == 101
    assert reset_response.resetTo == "claimed"
    assert reset_response.auditId == "adm_reset"

    requeue_response = await demo_ops.requeue_job(
        job_id="job-101",
        payload=SimpleNamespace(reason="requeue", force=False),
        db=object(),
        actor=SimpleNamespace(actor_id="actor-1"),
    )
    assert requeue_response.jobId == "job-101"
    assert requeue_response.previousStatus == "dead_letter"
    assert requeue_response.newStatus == "queued"

    fallback_response = await demo_ops.use_simulation_fallback(
        simulation_id=44,
        payload=SimpleNamespace(
            scenarioVersionId=9,
            applyTo="future_invites_only",
            reason="fallback",
            dryRun=False,
        ),
        db=object(),
        actor=SimpleNamespace(actor_id="actor-1"),
    )
    assert fallback_response.simulationId == 44
    assert fallback_response.activeScenarioVersionId == 9
    assert fallback_response.applyTo == "future_invites_only"


def test_configure_perf_logging_enabled(monkeypatch):
    monkeypatch.setattr(middleware_perf, "perf_logging_enabled", lambda: True)
    calls: dict[str, object] = {}

    class DummyEngine:
        sync_engine = object()

    def _attach(engine):
        calls["engine"] = engine

    monkeypatch.setattr("app.core.db.engine", DummyEngine(), raising=False)
    monkeypatch.setattr(
        "app.core.perf.attach_sqlalchemy_listeners",
        _attach,
        raising=False,
    )

    class DummyApp:
        def __init__(self):
            self.middlewares: list[object] = []

        def add_middleware(self, middleware):
            self.middlewares.append(middleware)

    app = DummyApp()
    middleware_perf.configure_perf_logging(app)

    from app.core import db

    assert calls["engine"] is db.engine
    assert middleware_perf.RequestPerfMiddleware in app.middlewares


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
            scheduledStartAt=datetime.now(UTC),
            candidateTimezone="UTC",
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
        id=10,
        day_index=2,
        title="Task",
        type="code",
        description="desc",
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

    def _build_response(*_args, **kwargs):
        return kwargs["day_audit"]

    monkeypatch.setattr(
        current_task_logic.cs_service,
        "fetch_owned_session",
        _fetch_owned_session,
    )
    monkeypatch.setattr(
        current_task_logic.cs_service,
        "ensure_schedule_started_for_content",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        current_task_logic.cs_service,
        "progress_snapshot",
        _progress_snapshot,
    )
    monkeypatch.setattr(current_task_logic.cs_repo, "get_day_audit", _get_day_audit)
    monkeypatch.setattr(
        current_task_logic,
        "build_current_task_response",
        _build_response,
    )
    monkeypatch.setattr(
        current_task_logic.rate_limit,
        "rate_limit_enabled",
        lambda: False,
    )

    day_audit = await current_task_logic.build_current_task_view(
        5,
        request,
        SimpleNamespace(sub="auth0|candidate"),
        object(),
    )
    assert captured["day_audit_called"] == (5, 2)
    assert day_audit.cutoff_commit_sha == "sha"


def test_resolve_simulation_summary_includes_content_sections_branch():
    summary = cs_responses._resolve_simulation_summary(
        SimpleNamespace(
            simulation=SimpleNamespace(id=1, title="Demo Simulation", role="Backend")
        ),
        include_content_sections=True,
    )
    assert summary.id == 1
    assert summary.title == "Demo Simulation"
    assert summary.role == "Backend"


def test_task_draft_finalization_payload_builder():
    payload = finalization.build_submission_payload(
        content_text="draft content",
        content_json={"delta": 1},
    )
    assert payload.contentText == "draft content"
    assert payload.contentJson == {"delta": 1}
