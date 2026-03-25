from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_orders_candidates_and_assigns_deterministic_display_names(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session,
        email="compare-ordering@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)

    first = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="   ",
        invite_email="order-first@example.com",
        status="not_started",
    )
    second = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="Katherine Johnson",
        invite_email="order-second@example.com",
        status="not_started",
    )
    third = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="",
        invite_email="order-third@example.com",
        status="not_started",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(recruiter),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert [row["candidateSessionId"] for row in payload["candidates"]] == [
        first.id,
        second.id,
        third.id,
    ]
    assert [row["candidateName"] for row in payload["candidates"]] == [
        "Candidate A",
        "Katherine Johnson",
        "Candidate C",
    ]
    assert [row["candidateDisplayName"] for row in payload["candidates"]] == [
        "Candidate A",
        "Katherine Johnson",
        "Candidate C",
    ]
