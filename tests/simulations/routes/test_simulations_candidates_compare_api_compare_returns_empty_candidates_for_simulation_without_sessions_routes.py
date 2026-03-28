from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_returns_empty_candidates_for_simulation_without_sessions(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session,
        email="compare-empty-owner@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    await async_session.commit()

    response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(recruiter),
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"simulationId": simulation.id, "candidates": []}
