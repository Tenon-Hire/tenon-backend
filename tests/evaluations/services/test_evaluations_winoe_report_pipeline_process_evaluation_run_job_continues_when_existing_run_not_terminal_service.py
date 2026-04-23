from __future__ import annotations

import pytest

from app.ai import build_ai_policy_snapshot
from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_pipeline_execute_service as execute_service,
)
from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_process_evaluation_run_job_continues_when_existing_run_not_terminal(
    monkeypatch,
):
    db = SimpleNamespace(commit=AsyncMock())
    trial = SimpleNamespace(
        id=70,
        company_id=80,
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=50, scenario_version_id=60, trial_id=70),
        trial=trial,
        scenario_version=SimpleNamespace(
            rubric_version="rubric-vx",
            ai_policy_snapshot_json=build_ai_policy_snapshot(trial=trial),
        ),
    )
    existing_run = SimpleNamespace(id=99, status="running")
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value=SimpleNamespace(
                day_results=[],
                overall_winoe_score=82,
                recommendation="hire",
                confidence=0.77,
                report_json={"summary": "in_progress_then_completed"},
            )
        )
    )
    start_run = AsyncMock(side_effect=AssertionError("start_run should not be called"))
    complete_run = AsyncMock(
        return_value=SimpleNamespace(
            id=99,
            generated_at=datetime(2026, 3, 19, 0, 5, tzinfo=UTC),
            model_version="2026-03-12",
            prompt_version="winoe-report-v1",
            rubric_version="rubric-vx",
            basis_fingerprint="basis-99",
        )
    )

    monkeypatch.setattr(
        winoe_report_pipeline,
        "async_session_maker",
        _session_maker_for(db),
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
        winoe_report_pipeline,
        "_submissions_by_day",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "_day_audits_by_day",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "_resolve_day4_transcript",
        AsyncMock(return_value=(None, "transcript:missing")),
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_repo,
        "get_run_by_job_id",
        AsyncMock(return_value=existing_run),
    )
    monkeypatch.setattr(winoe_report_pipeline.evaluation_runs, "start_run", start_run)
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_runs,
        "complete_run",
        complete_run,
    )
    monkeypatch.setattr(
        winoe_report_pipeline.winoe_report_repository,
        "upsert_marker",
        AsyncMock(),
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

    response = await winoe_report_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 50,
            "companyId": 80,
            "requestedByUserId": 77,
            "jobId": "job-abc",
        }
    )
    assert response["status"] == "completed"
    assert response["evaluationRunId"] == 99
    start_run.assert_not_awaited()
    complete_run.assert_awaited_once()
    assert complete_run.await_args.kwargs["run_id"] == 99
