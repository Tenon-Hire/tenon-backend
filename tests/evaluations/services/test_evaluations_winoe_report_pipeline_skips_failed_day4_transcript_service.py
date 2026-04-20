from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai import build_ai_policy_snapshot
from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_pipeline_runner_service as runner_service,
)
from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_process_evaluation_run_job_skips_failed_day4_transcript(monkeypatch):
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
    captured = {}

    async def _fake_evaluate_and_finalize_run(**kwargs):
        captured["bundle"] = kwargs["bundle"]
        return SimpleNamespace(
            id=123,
            model_version="2026-03-12",
            prompt_version="winoe-report-v1",
            rubric_version="rubric-vx",
            basis_fingerprint="basis-123",
            generated_at=None,
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
        winoe_report_pipeline,
        "_tasks_by_day",
        AsyncMock(return_value={4: SimpleNamespace(id=14, type="handoff")}),
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "_submissions_by_day",
        AsyncMock(
            return_value={
                4: SimpleNamespace(
                    id=24,
                    content_text=None,
                    content_json=None,
                    code_repo_path=None,
                    commit_sha=None,
                    workflow_run_id=None,
                    diff_summary_json=None,
                    tests_passed=None,
                    tests_failed=None,
                )
            }
        ),
    )
    monkeypatch.setattr(
        winoe_report_pipeline, "_day_audits_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "_resolve_day4_transcript",
        AsyncMock(
            return_value=(
                SimpleNamespace(
                    id=24,
                    status="failed",
                    text=None,
                    segments_json=None,
                    model_name=None,
                ),
                "transcript:24:failed",
                "failed",
            )
        ),
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_repo,
        "get_run_by_job_id",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_runs,
        "start_run",
        AsyncMock(
            return_value=SimpleNamespace(
                id=123,
                status="running",
                basis_fingerprint="basis-123",
                generated_at=None,
            )
        ),
    )
    monkeypatch.setattr(
        runner_service,
        "_build_run_metadata",
        lambda **_kwargs: (
            {"basisFingerprint": "basis-123"},
            {},
            "day2-sha",
            "day3-sha",
            "cutoff-sha",
        ),
    )
    monkeypatch.setattr(
        runner_service, "_evaluate_and_finalize_run", _fake_evaluate_and_finalize_run
    )

    await winoe_report_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 50,
            "companyId": 80,
            "requestedByUserId": 77,
            "jobId": "job-abc",
        }
    )

    assert captured["bundle"].disabled_day_indexes == [4]
    assert captured["bundle"].day_inputs[3].transcript_segments == []


@pytest.mark.asyncio
async def test_process_evaluation_run_job_skips_missing_day4_transcript(monkeypatch):
    db = SimpleNamespace(commit=AsyncMock())
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
    captured = {}

    async def _fake_evaluate_and_finalize_run(**kwargs):
        captured["bundle"] = kwargs["bundle"]
        return SimpleNamespace(
            id=124,
            model_version="2026-03-12",
            prompt_version="winoe-report-v1",
            rubric_version="rubric-vx",
            basis_fingerprint="basis-123",
            generated_at=None,
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
        winoe_report_pipeline,
        "_tasks_by_day",
        AsyncMock(return_value={4: SimpleNamespace(id=15, type="handoff")}),
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "_submissions_by_day",
        AsyncMock(
            return_value={
                4: SimpleNamespace(
                    id=25,
                    content_text=None,
                    content_json=None,
                    code_repo_path=None,
                    commit_sha=None,
                    workflow_run_id=None,
                    diff_summary_json=None,
                    tests_passed=None,
                    tests_failed=None,
                )
            }
        ),
    )
    monkeypatch.setattr(
        winoe_report_pipeline, "_day_audits_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "_resolve_day4_transcript",
        AsyncMock(
            return_value=(
                None,
                "transcript:missing",
                "missing",
            )
        ),
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_repo,
        "get_run_by_job_id",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        winoe_report_pipeline.evaluation_runs,
        "start_run",
        AsyncMock(
            return_value=SimpleNamespace(
                id=124,
                status="running",
                basis_fingerprint="basis-123",
                generated_at=None,
            )
        ),
    )
    monkeypatch.setattr(
        runner_service,
        "_build_run_metadata",
        lambda **_kwargs: (
            {"basisFingerprint": "basis-123"},
            {},
            "day2-sha",
            "day3-sha",
            "cutoff-sha",
        ),
    )
    monkeypatch.setattr(
        runner_service, "_evaluate_and_finalize_run", _fake_evaluate_and_finalize_run
    )

    await winoe_report_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 51,
            "companyId": 81,
            "requestedByUserId": 77,
            "jobId": "job-xyz",
        }
    )

    assert captured["bundle"].disabled_day_indexes == [4]
    assert captured["bundle"].day_inputs[3].transcript_segments == []
