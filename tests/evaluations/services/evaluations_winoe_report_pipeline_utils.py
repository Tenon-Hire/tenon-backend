from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.ai import build_ai_policy_snapshot
from app.evaluations.repositories import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
)
from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_pipeline_execute_service as execute_service,
)
from app.evaluations.services import winoe_report_pipeline


class _ScalarOneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    def __init__(self, *, get_value=None, execute_values=None):
        self._get_value = get_value
        self._execute_values = list(execute_values or [])

    async def get(self, *_args, **_kwargs):
        return self._get_value

    async def execute(self, *_args, **_kwargs):
        value = self._execute_values.pop(0) if self._execute_values else None
        return _ScalarOneResult(value)


class _SessionContext:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


def _session_maker_for(db):
    def _maker():
        return _SessionContext(db)

    return _maker


def _setup_pipeline_process_job_happy_path(monkeypatch):
    db = SimpleNamespace(commit=AsyncMock())
    trial = SimpleNamespace(
        id=70,
        company_id=80,
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    ai_policy_snapshot_json = build_ai_policy_snapshot(trial=trial)
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=50, scenario_version_id=60, trial_id=70),
        trial=trial,
        scenario_version=SimpleNamespace(
            rubric_version="rubric-vx",
            ai_policy_snapshot_json=ai_policy_snapshot_json,
        ),
    )
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value=SimpleNamespace(
                day_results=[],
                overall_winoe_score=87,
                recommendation="strong_hire",
                confidence=0.91,
                report_json={"summary": "ok"},
            )
        )
    )
    get_run_by_job_id = AsyncMock(return_value=None)
    get_latest_run_for_candidate_session = AsyncMock(return_value=None)
    start_run = AsyncMock(return_value=SimpleNamespace(id=123, status="running"))
    complete_run = AsyncMock(
        return_value=SimpleNamespace(
            id=123,
            generated_at=datetime(2026, 3, 19, 0, 0, tzinfo=UTC),
            model_version="2026-03-12",
            prompt_version="winoe-report-v1",
            rubric_version="rubric-vx",
            basis_fingerprint="basis-123",
        )
    )
    monkeypatch.setattr(
        winoe_report_pipeline, "async_session_maker", _session_maker_for(db)
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        winoe_report_pipeline, "has_company_access", lambda **_kwargs: True
    )
    monkeypatch.setattr(
        winoe_report_pipeline, "_tasks_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        winoe_report_pipeline, "_submissions_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        winoe_report_pipeline, "_day_audits_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "_resolve_day4_transcript",
        AsyncMock(return_value=(None, "transcript:missing")),
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_repo, "get_run_by_job_id", get_run_by_job_id
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_repo,
        "get_latest_run_for_candidate_session",
        get_latest_run_for_candidate_session,
    )
    monkeypatch.setattr(winoe_report_pipeline.evaluation_runs, "start_run", start_run)
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_runs, "complete_run", complete_run
    )
    monkeypatch.setattr(
        winoe_report_pipeline.winoe_report_repository, "upsert_marker", AsyncMock()
    )
    monkeypatch.setattr(
        execute_service.notification_service,
        "enqueue_winoe_report_ready_notification",
        AsyncMock(),
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluator_service,
        "get_winoe_report_evaluator",
        lambda: evaluator,
    )
    return get_run_by_job_id, get_latest_run_for_candidate_session, start_run


__all__ = [name for name in globals() if not name.startswith("__")]
