from __future__ import annotations

import pytest

from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_put_then_get_task_draft_round_trips(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="draft-put-get@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session, trial=sim, status="in_progress", with_default_schedule=True
    )
    await async_session.commit()
    day1_task = tasks[0]
    headers = candidate_header_factory(candidate_session)
    payload = {
        "contentText": "## Plan\n- step 1",
        "contentJson": {
            "reflection": {"challenges": "api design", "decisions": "favor idempotency"}
        },
    }

    put_response = await async_client.put(
        f"/api/tasks/{day1_task.id}/draft", headers=headers, json=payload
    )
    assert put_response.status_code == 200, put_response.text
    put_body = put_response.json()
    assert put_body["taskId"] == day1_task.id
    assert put_body["updatedAt"] is not None

    get_response = await async_client.get(
        f"/api/tasks/{day1_task.id}/draft", headers=headers
    )
    assert get_response.status_code == 200, get_response.text
    get_body = get_response.json()
    assert get_body["taskId"] == day1_task.id
    assert get_body["contentText"] == payload["contentText"]
    assert get_body["contentJson"] == payload["contentJson"]
    assert get_body["updatedAt"] == put_body["updatedAt"]
    assert get_body["finalizedAt"] is None
    assert get_body["finalizedSubmissionId"] is None


@pytest.mark.asyncio
async def test_get_task_draft_missing_returns_not_found(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="draft-missing@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session, trial=sim, status="in_progress", with_default_schedule=True
    )
    await async_session.commit()
    response = await async_client.get(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=candidate_header_factory(candidate_session),
    )
    assert response.status_code == 404, response.text
    assert response.json()["errorCode"] == "DRAFT_NOT_FOUND"
