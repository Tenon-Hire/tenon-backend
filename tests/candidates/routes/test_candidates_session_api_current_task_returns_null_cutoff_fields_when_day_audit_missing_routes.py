from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_current_task_returns_null_cutoff_fields_when_day_audit_missing(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="current-cutoff-missing@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["currentTask"]["dayIndex"] == 2
    assert body["currentTask"]["cutoffCommitSha"] is None
    assert body["currentTask"]["cutoffAt"] is None
