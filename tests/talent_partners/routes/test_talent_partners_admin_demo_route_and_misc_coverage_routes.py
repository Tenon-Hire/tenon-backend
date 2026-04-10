from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.shared.http import shared_http_middleware_perf_middleware as middleware_perf
from app.talent_partners.routes.admin_routes import demo_ops
from app.talent_partners.services import (
    talent_partners_services_talent_partners_admin_ops_service as admin_ops_service,
)


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
        "use_trial_fallback_scenario",
        AsyncMock(
            return_value=admin_ops_service.TrialFallbackResult(
                trial_id=44,
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

    fallback_response = await demo_ops.use_trial_fallback(
        trial_id=44,
        payload=SimpleNamespace(
            scenarioVersionId=9,
            applyTo="future_invites_only",
            reason="fallback",
            dryRun=False,
        ),
        db=object(),
        actor=SimpleNamespace(actor_id="actor-1"),
    )
    assert fallback_response.trialId == 44
    assert fallback_response.activeScenarioVersionId == 9
    assert fallback_response.applyTo == "future_invites_only"


def test_configure_perf_logging_enabled(monkeypatch):
    monkeypatch.setattr(middleware_perf, "perf_logging_enabled", lambda: True)
    calls: dict[str, object] = {}

    class DummyEngine:
        sync_engine = object()

    monkeypatch.setattr("app.shared.database.engine", DummyEngine(), raising=False)
    monkeypatch.setattr(
        "app.shared.perf.attach_sqlalchemy_listeners",
        lambda engine: calls.__setitem__("engine", engine),
        raising=False,
    )

    class DummyApp:
        def __init__(self):
            self.middlewares: list[object] = []

        def add_middleware(self, middleware):
            self.middlewares.append(middleware)

    app = DummyApp()
    middleware_perf.configure_perf_logging(app)
    from app.shared.utils import shared_utils_db_utils as db

    assert calls["engine"] is db.engine
    assert middleware_perf.RequestPerfMiddleware in app.middlewares
