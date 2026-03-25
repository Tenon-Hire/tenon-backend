from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_returns_404_for_unknown_simulation(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session,
        email="compare-404@test.com",
    )
    await async_session.commit()

    response = await async_client.get(
        "/api/simulations/999999/candidates/compare",
        headers=auth_header_factory(recruiter),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Simulation not found"
