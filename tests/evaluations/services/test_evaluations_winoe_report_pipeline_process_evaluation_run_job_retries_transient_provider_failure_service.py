from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations.winoe_report_review import WinoeReportReviewProviderError
from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_process_evaluation_run_job_retries_transient_provider_failure(
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
        candidate_session=SimpleNamespace(id=50, scenario_version_id=60),
        trial=trial,
        scenario_version=SimpleNamespace(
            rubric_version="rubric-vx",
            ai_policy_snapshot_json=build_ai_policy_snapshot(trial=trial),
        ),
    )
    fail_run = AsyncMock()
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            side_effect=WinoeReportReviewProviderError(
                "openai_request_failed:RateLimitError"
            )
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
        winoe_report_pipeline.evaluation_repo,
        "get_run_by_job_id",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_runs,
        "start_run",
        AsyncMock(return_value=SimpleNamespace(id=123, status="running")),
    )
    monkeypatch.setattr(winoe_report_pipeline.evaluation_runs, "fail_run", fail_run)
    monkeypatch.setattr(
        winoe_report_pipeline.evaluator_service,
        "get_winoe_report_evaluator",
        lambda: evaluator,
    )

    with pytest.raises(
        WinoeReportReviewProviderError, match="openai_request_failed:RateLimitError"
    ):
        await winoe_report_pipeline.process_evaluation_run_job(
            {
                "candidateSessionId": 50,
                "companyId": 80,
                "requestedByUserId": 77,
                "jobId": "job-abc",
            }
        )

    fail_run.assert_not_awaited()
