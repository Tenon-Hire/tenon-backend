from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_candidate_invites_hide_terminated_by_default(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="candidate-filter@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="candidate-filter@example.com",
    )
    await async_session.commit()

    terminated = await async_client.post(
        f"/api/simulations/{simulation.id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminated.status_code == 200, terminated.text

    default_invites = await async_client.get(
        "/api/candidate/invites",
        headers={"Authorization": "Bearer candidate:candidate-filter@example.com"},
    )
    assert default_invites.status_code == 200, default_invites.text
    assert default_invites.json() == []

    include_terminated = await async_client.get(
        "/api/candidate/invites?includeTerminated=true",
        headers={"Authorization": "Bearer candidate:candidate-filter@example.com"},
    )
    assert include_terminated.status_code == 200, include_terminated.text
    rows = include_terminated.json()
    assert len(rows) == 1
    assert rows[0]["candidateSessionId"] == candidate_session.id
