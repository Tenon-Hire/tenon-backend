from __future__ import annotations

import pytest

from tests.evaluations.routes.evaluations_winoe_report_api_utils import *


@pytest.mark.asyncio
async def test_generate_winoe_report_returns_queued_and_get_running(
    async_client,
    async_session,
    auth_header_factory,
):
    talent_partner, candidate_session = await _seed_completed_candidate_session(
        async_session
    )

    before_generate = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report",
        headers=auth_header_factory(talent_partner),
    )
    assert before_generate.status_code == 200, before_generate.text
    assert before_generate.json() == {"status": "not_started"}

    generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report/generate",
        headers=auth_header_factory(talent_partner),
    )
    assert generate.status_code == 202, generate.text
    body = generate.json()
    assert body["status"] == "queued"
    assert isinstance(body["jobId"], str)

    job = await async_session.get(Job, body["jobId"])
    assert job is not None
    assert job.job_type == EVALUATION_RUN_JOB_TYPE
    assert job.candidate_session_id == candidate_session.id

    fetch = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report",
        headers=auth_header_factory(talent_partner),
    )
    assert fetch.status_code == 200, fetch.text
    assert fetch.json() == {"status": "running"}
