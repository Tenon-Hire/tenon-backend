from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai import build_ai_policy_snapshot, compute_ai_policy_snapshot_digest
from app.evaluations.services import winoe_report_api
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_metadata_service import (
    _build_run_metadata,
)
from tests.evaluations.services.evaluations_winoe_report_api_utils import build_context


@pytest.mark.asyncio
async def test_generate_winoe_report_queues_job(monkeypatch):
    context = build_context(candidate_session_id=77, company_id=88)

    async def _require(_db, *, candidate_session_id, user):
        assert candidate_session_id == 77
        assert user.id == 44
        return context

    enqueue = AsyncMock(return_value=SimpleNamespace(id="job-77"))
    monkeypatch.setattr(
        winoe_report_api, "require_talent_partner_candidate_session_context", _require
    )
    monkeypatch.setattr(
        winoe_report_api,
        "_build_generation_basis_fingerprint",
        AsyncMock(return_value="basis-77"),
    )
    monkeypatch.setattr(winoe_report_api, "enqueue_evaluation_run", enqueue)
    response = await winoe_report_api.generate_winoe_report(
        object(), candidate_session_id=77, user=SimpleNamespace(id=44)
    )
    assert response == {"jobId": "job-77", "status": "queued"}
    enqueue.assert_awaited_once()
    assert enqueue.await_args.kwargs["basis_fingerprint"] == "basis-77"


@pytest.mark.asyncio
async def test_generate_winoe_report_reuses_job_for_same_basis(monkeypatch):
    context = build_context(candidate_session_id=78, company_id=88)

    async def _require(_db, *, candidate_session_id, user):
        assert candidate_session_id == 78
        assert user.id == 44
        return context

    enqueue = AsyncMock(
        side_effect=[SimpleNamespace(id="job-78"), SimpleNamespace(id="job-78")]
    )
    monkeypatch.setattr(
        winoe_report_api, "require_talent_partner_candidate_session_context", _require
    )
    monkeypatch.setattr(
        winoe_report_api,
        "_build_generation_basis_fingerprint",
        AsyncMock(return_value="basis-78"),
    )
    monkeypatch.setattr(winoe_report_api, "enqueue_evaluation_run", enqueue)

    first = await winoe_report_api.generate_winoe_report(
        object(), candidate_session_id=78, user=SimpleNamespace(id=44)
    )
    second = await winoe_report_api.generate_winoe_report(
        object(), candidate_session_id=78, user=SimpleNamespace(id=44)
    )

    assert first == {"jobId": "job-78", "status": "queued"}
    assert second == {"jobId": "job-78", "status": "queued"}
    assert enqueue.await_count == 2


@pytest.mark.asyncio
async def test_fetch_winoe_report_ready_uses_latest_success(monkeypatch):
    context = build_context(candidate_session_id=55, company_id=88)
    run = SimpleNamespace(id=1)
    monkeypatch.setattr(
        winoe_report_api,
        "require_talent_partner_candidate_session_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_successful_run_for_candidate_session",
        AsyncMock(return_value=run),
    )
    monkeypatch.setattr(
        winoe_report_api,
        "build_ready_payload",
        lambda value: {"status": "ready", "reportRunId": value.id},
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_run_for_candidate_session",
        AsyncMock(return_value=None),
    )
    response = await winoe_report_api.fetch_winoe_report(
        object(), candidate_session_id=55, user=SimpleNamespace(id=1)
    )
    assert response == {"status": "ready", "reportRunId": 1}


@pytest.mark.asyncio
async def test_fetch_winoe_report_prefers_latest_success_over_newer_running_rerun(
    monkeypatch,
):
    context = build_context(candidate_session_id=56, company_id=88)
    latest_success = SimpleNamespace(id=1, status="completed")
    newer_run = SimpleNamespace(id=2, status="running", error_code=None)
    monkeypatch.setattr(
        winoe_report_api,
        "require_talent_partner_candidate_session_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_successful_run_for_candidate_session",
        AsyncMock(return_value=latest_success),
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_run_for_candidate_session",
        AsyncMock(return_value=newer_run),
    )
    monkeypatch.setattr(
        winoe_report_api,
        "build_ready_payload",
        lambda value: {"status": "ready", "reportRunId": value.id},
    )

    response = await winoe_report_api.fetch_winoe_report(
        object(), candidate_session_id=56, user=SimpleNamespace(id=1)
    )

    assert response == {"status": "ready", "reportRunId": 1}


@pytest.mark.asyncio
async def test_fetch_winoe_report_prefers_latest_success_over_newer_failed_rerun(
    monkeypatch,
):
    context = build_context(candidate_session_id=57, company_id=88)
    latest_success = SimpleNamespace(id=1, status="completed")
    newer_run = SimpleNamespace(id=2, status="failed", error_code="evaluation_failed")
    monkeypatch.setattr(
        winoe_report_api,
        "require_talent_partner_candidate_session_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_successful_run_for_candidate_session",
        AsyncMock(return_value=latest_success),
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_run_for_candidate_session",
        AsyncMock(return_value=newer_run),
    )
    monkeypatch.setattr(
        winoe_report_api,
        "build_ready_payload",
        lambda value: {"status": "ready", "reportRunId": value.id},
    )

    response = await winoe_report_api.fetch_winoe_report(
        object(), candidate_session_id=57, user=SimpleNamespace(id=1)
    )

    assert response == {"status": "ready", "reportRunId": 1}


@pytest.mark.asyncio
async def test_build_generation_basis_fingerprint_matches_run_metadata(monkeypatch):
    trial = SimpleNamespace(
        id=91,
        company_id=101,
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=201, scenario_version_id=301),
        trial=trial,
        scenario_version=SimpleNamespace(
            rubric_version="rubric-vx",
            ai_policy_snapshot_json=build_ai_policy_snapshot(trial=trial),
        ),
    )
    monkeypatch.setattr(winoe_report_api, "_tasks_by_day", AsyncMock(return_value={}))
    monkeypatch.setattr(
        winoe_report_api, "_submissions_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        winoe_report_api, "_day_audits_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        winoe_report_api,
        "_resolve_day4_transcript",
        AsyncMock(return_value=(None, "transcript:missing")),
    )

    fingerprint = await winoe_report_api._build_generation_basis_fingerprint(
        object(), context=context
    )
    run_metadata, *_ = _build_run_metadata(
        context=context,
        scenario_rubric_version="rubric-vx",
        day_audits={},
        submissions_by_day={},
        transcript_reference="transcript:missing",
        transcript=None,
        disabled_days=[4],
        enabled_days=[1, 2, 3, 4, 5],
        requested_by_user_id=None,
        job_id=None,
        ai_policy_snapshot_digest=compute_ai_policy_snapshot_digest(
            context.scenario_version.ai_policy_snapshot_json
        ),
    )

    assert fingerprint == run_metadata["basisFingerprint"]
