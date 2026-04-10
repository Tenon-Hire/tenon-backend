from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_api_utils import *


@pytest.mark.asyncio
async def test_current_task_rejects_non_positive_session_header(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="header-zero@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="header-zero-owner@example.com",
        with_default_schedule=False,
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:header-zero-owner@example.com",
            "x-candidate-session-id": "0",
        },
    )
    assert response.status_code == 401, response.text
    assert response.json()["errorCode"] == "CANDIDATE_SESSION_HEADER_REQUIRED"
