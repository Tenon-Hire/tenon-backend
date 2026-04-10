from __future__ import annotations

import pytest

from tests.evaluations.routes.evaluations_winoe_report_api_utils import *


@pytest.mark.asyncio
async def test_winoe_report_failure_surface_when_latest_run_failed(
    async_client,
    async_session,
    auth_header_factory,
    monkeypatch,
):
    talent_partner, candidate_session = await _seed_completed_candidate_session(
        async_session
    )

    class _FailingEvaluator:
        async def evaluate(self, _bundle):
            raise RuntimeError("forced evaluator failure")

    monkeypatch.setattr(
        "app.evaluations.services.winoe_report_pipeline.evaluator_service.get_winoe_report_evaluator",
        lambda: _FailingEvaluator(),
    )

    generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report/generate",
        headers=auth_header_factory(talent_partner),
    )
    assert generate.status_code == 202, generate.text
    generated_job_id = generate.json()["jobId"]

    handled = await _run_worker_once(
        async_session, worker_id="winoe-report-worker-failed"
    )
    assert handled is True

    runs = await evaluation_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    assert len(runs) == 1
    assert runs[0].status == EVALUATION_RUN_STATUS_FAILED
    assert runs[0].error_code == "evaluation_failed"
    assert runs[0].job_id == generated_job_id

    durable_job = await async_session.get(Job, generated_job_id)
    assert durable_job is not None
    assert durable_job.status == JOB_STATUS_DEAD_LETTER

    marker = (
        await async_session.execute(
            select(WinoeReport).where(
                WinoeReport.candidate_session_id == candidate_session.id
            )
        )
    ).scalar_one_or_none()
    assert marker is None

    fetch = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report",
        headers=auth_header_factory(talent_partner),
    )
    assert fetch.status_code == 200, fetch.text
    assert fetch.json() == {"status": "failed", "errorCode": "evaluation_failed"}
