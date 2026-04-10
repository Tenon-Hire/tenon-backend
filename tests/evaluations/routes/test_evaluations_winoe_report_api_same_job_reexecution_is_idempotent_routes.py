from __future__ import annotations

import pytest

from tests.evaluations.routes.evaluations_winoe_report_api_utils import *


@pytest.mark.asyncio
async def test_winoe_report_same_job_reexecution_is_idempotent(
    async_client,
    async_session,
    auth_header_factory,
):
    talent_partner, candidate_session = await _seed_completed_candidate_session(
        async_session
    )

    generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report/generate",
        headers=auth_header_factory(talent_partner),
    )
    assert generate.status_code == 202, generate.text
    job_id = generate.json()["jobId"]

    job = await async_session.get(Job, job_id)
    assert job is not None
    payload = dict(job.payload_json)

    first = await handle_evaluation_run(payload)
    second = await handle_evaluation_run(payload)

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert first["evaluationRunId"] == second["evaluationRunId"]

    runs = await evaluation_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    assert len(runs) == 1
    assert runs[0].job_id == job_id
