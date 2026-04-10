from __future__ import annotations

import pytest

from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)
from tests.tasks.routes.test_tasks_drafts_api_utils import set_closed_schedule


@pytest.mark.asyncio
async def test_put_task_draft_outside_window_returns_task_window_closed(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="draft-window@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session, trial=sim, status="in_progress", with_default_schedule=False
    )
    await async_session.commit()
    await set_closed_schedule(async_session, candidate_session_id=candidate_session.id)

    response = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=candidate_header_factory(candidate_session),
        json={"contentText": "not now"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["errorCode"] == "TASK_WINDOW_CLOSED"


@pytest.mark.asyncio
async def test_put_task_draft_after_submission_returns_draft_finalized(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="draft-finalized@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session, trial=sim, status="in_progress", with_default_schedule=True
    )
    await async_session.commit()

    headers = candidate_header_factory(candidate_session)
    put_first = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=headers,
        json={"contentText": "before submit"},
    )
    assert put_first.status_code == 200, put_first.text
    submit_response = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=headers,
        json={"contentText": "manual submit wins"},
    )
    assert submit_response.status_code == 201, submit_response.text
    put_second = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=headers,
        json={"contentText": "should fail"},
    )
    assert put_second.status_code == 409, put_second.text
    assert put_second.json()["errorCode"] == "DRAFT_FINALIZED"
