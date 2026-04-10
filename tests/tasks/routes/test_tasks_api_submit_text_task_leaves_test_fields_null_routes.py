from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_text_task_leaves_test_fields_null(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="text-submit@sim.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )

    headers = candidate_header_factory(cs)
    resp = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=headers,
        json={"contentText": "design answer"},
    )

    assert resp.status_code == 201, resp.text
    sub = await async_session.get(Submission, resp.json()["submissionId"])
    assert sub.tests_passed is None
    assert sub.tests_failed is None
    assert sub.test_output is None
    assert sub.last_run_at is None
