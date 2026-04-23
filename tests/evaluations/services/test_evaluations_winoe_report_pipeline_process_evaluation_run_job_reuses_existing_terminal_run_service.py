from __future__ import annotations

import pytest

from app.ai import build_ai_policy_snapshot
from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("run_status", "error_code", "expected_status"),
    [
        (EVALUATION_RUN_STATUS_COMPLETED, None, "completed"),
        (EVALUATION_RUN_STATUS_FAILED, "evaluation_failed", "failed"),
    ],
)
async def test_process_evaluation_run_job_reuses_existing_terminal_run(
    monkeypatch,
    run_status,
    error_code,
    expected_status,
):
    db = SimpleNamespace()
    trial = SimpleNamespace(
        id=70,
        company_id=80,
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=50, scenario_version_id=60),
        trial=trial,
        scenario_version=SimpleNamespace(
            rubric_version="rubric-vx",
            ai_policy_snapshot_json=build_ai_policy_snapshot(trial=trial),
        ),
    )
    existing_run = SimpleNamespace(
        id=99,
        status=run_status,
        model_version="2026-03-12",
        prompt_version="winoe-report-v1",
        rubric_version="rubric-vx",
        basis_fingerprint="abc123",
        error_code=error_code,
    )

    start_run = AsyncMock(side_effect=AssertionError("start_run should not be called"))
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

    response = await winoe_report_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 50,
            "companyId": 80,
            "requestedByUserId": 77,
            "jobId": "job-abc",
        }
    )
    assert response["status"] == expected_status
    assert response["candidateSessionId"] == 50
    assert response["evaluationRunId"] == 99
    start_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_evaluation_run_job_reuses_existing_run_by_basis_when_job_missing(
    monkeypatch,
):
    db = SimpleNamespace()
    trial = SimpleNamespace(
        id=71,
        company_id=81,
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=51, scenario_version_id=61),
        trial=trial,
        scenario_version=SimpleNamespace(
            rubric_version="rubric-vx",
            ai_policy_snapshot_json=build_ai_policy_snapshot(trial=trial),
        ),
    )
    existing_run = SimpleNamespace(
        id=101,
        status="running",
        model_version="2026-03-12",
        prompt_version="winoe-report-v1",
        rubric_version="rubric-vx",
        basis_fingerprint="basis-101",
    )

    start_run = AsyncMock(side_effect=AssertionError("start_run should not be called"))
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
        AsyncMock(return_value=None),
    )
    get_latest_run_for_candidate_session = AsyncMock(return_value=existing_run)
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_repo,
        "get_latest_run_for_candidate_session",
        get_latest_run_for_candidate_session,
    )
    monkeypatch.setattr(winoe_report_pipeline.evaluation_runs, "start_run", start_run)

    response = await winoe_report_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 51,
            "companyId": 81,
            "requestedByUserId": 77,
        }
    )
    assert response["status"] == "running"
    assert response["candidateSessionId"] == 51
    assert response["evaluationRunId"] == 101
    assert response["basisFingerprint"] == "basis-101"
    start_run.assert_not_awaited()
    winoe_report_pipeline.evaluation_repo.get_run_by_job_id.assert_not_awaited()
    get_latest_run_for_candidate_session.assert_awaited_once()
    assert (
        get_latest_run_for_candidate_session.await_args.kwargs["candidate_session_id"]
        == 51
    )
    assert get_latest_run_for_candidate_session.await_args.kwargs["basis_fingerprint"]
