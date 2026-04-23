from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_process_evaluation_run_job_skips_job_lookup_when_job_id_missing(
    monkeypatch,
):
    (
        get_run_by_job_id,
        get_latest_run_for_candidate_session,
        start_run,
    ) = _setup_pipeline_process_job_happy_path(monkeypatch)

    response = await winoe_report_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 50,
            "companyId": 80,
            "requestedByUserId": 77,
        }
    )
    assert response["status"] == "completed"
    assert response["evaluationRunId"] == 123
    get_run_by_job_id.assert_not_awaited()
    get_latest_run_for_candidate_session.assert_awaited_once()
    assert (
        get_latest_run_for_candidate_session.await_args.kwargs["candidate_session_id"]
        == 50
    )
    start_run.assert_awaited_once()
