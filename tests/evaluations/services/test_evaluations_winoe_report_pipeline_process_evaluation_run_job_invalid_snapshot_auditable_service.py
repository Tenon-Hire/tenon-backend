from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai import (
    build_ai_policy_snapshot,
    compute_ai_policy_snapshot_basis_fingerprint,
)
from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_process_evaluation_run_job_persists_failed_run_for_invalid_snapshot(
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
    snapshot = build_ai_policy_snapshot(trial=trial)
    snapshot["snapshotDigest"] = "x" * 256
    snapshot["agents"]["codespace"] = {
        "key": "codespace",
        "promptVersion": "legacy",
        "rubricVersion": "legacy",
        "runtime": {
            "runtimeMode": "test",
            "provider": "openai",
            "model": "gpt-4.1",
            "timeoutSeconds": 1,
            "maxRetries": 0,
        },
        "policyFileName": "legacy.md",
        "policySha256": "legacy",
        "schemaFileName": "legacy.json",
        "schemaSha256": "legacy",
        "instructionsSha256": "legacy",
        "rubricSha256": "legacy",
        "resolvedInstructionsMd": "legacy",
        "resolvedRubricMd": "legacy",
    }
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=50, scenario_version_id=60),
        trial=trial,
        scenario_version=SimpleNamespace(
            rubric_version="rubric-vx",
            ai_policy_snapshot_json=snapshot,
        ),
    )
    start_run = AsyncMock(return_value=SimpleNamespace(id=456, status="running"))
    fail_run = AsyncMock(return_value=SimpleNamespace(id=456, status="failed"))
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
        winoe_report_pipeline.evaluation_runs,
        "start_run",
        start_run,
    )
    monkeypatch.setattr(winoe_report_pipeline.evaluation_runs, "fail_run", fail_run)

    response = await winoe_report_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 50,
            "companyId": 80,
            "requestedByUserId": 77,
            "jobId": "job-abc",
        }
    )

    assert response["status"] == "failed"
    assert response["candidateSessionId"] == 50
    assert response["evaluationRunId"] == 456
    assert (
        response["errorCode"]
        == "scenario_version_ai_policy_snapshot_agent_contract_mismatch"
    )
    start_run.assert_awaited_once()
    fail_run.assert_awaited_once()
    expected_basis_fingerprint = compute_ai_policy_snapshot_basis_fingerprint(snapshot)
    assert (
        start_run.await_args.kwargs["basis_fingerprint"] == expected_basis_fingerprint
    )
    assert len(start_run.await_args.kwargs["basis_fingerprint"]) == 64
    assert (
        start_run.await_args.kwargs["basis_fingerprint"] != snapshot["snapshotDigest"]
    )
    assert fail_run.await_args.kwargs["error_code"] == (
        "scenario_version_ai_policy_snapshot_agent_contract_mismatch"
    )
    metadata = fail_run.await_args.kwargs["metadata_json"]
    assert metadata["aiPolicySnapshotDigest"] == snapshot["snapshotDigest"]
    assert metadata["aiPolicySnapshotBasisFingerprint"] == expected_basis_fingerprint
    assert len(metadata["aiPolicySnapshotBasisFingerprint"]) == 64
    assert len(metadata["aiPolicySnapshotDigest"]) == 256
    assert metadata["aiPolicyProvider"] == "openai"
    assert metadata["aiPolicyModel"] == snapshot["agents"]["winoeReport"]["model"]
    assert (
        metadata["aiPolicyPromptVersion"]
        == snapshot["agents"]["winoeReport"]["promptVersion"]
    )
    assert (
        metadata["aiPolicyRubricVersion"]
        == snapshot["agents"]["winoeReport"]["rubricVersion"]
    )
    assert metadata["evaluationModelName"]
    assert metadata["evaluationModelVersion"]
    assert metadata["evaluationPromptVersion"]
    assert metadata["evaluationRubricVersion"] == "rubric-vx"
    assert db.commit.await_count == 1
