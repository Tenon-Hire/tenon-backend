from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_returns_403_for_forbidden_company_or_scope(
    async_client, async_session, auth_header_factory
):
    owner_company = await create_company(async_session, name="Owner Compare Co")
    owner = await create_recruiter(
        async_session,
        company=owner_company,
        email="compare-owner-forbidden@test.com",
    )
    same_company_non_owner = await create_recruiter(
        async_session,
        company=owner_company,
        email="compare-peer@test.com",
    )
    other_company = await create_company(async_session, name="Other Compare Co")
    other_recruiter = await create_recruiter(
        async_session,
        company=other_company,
        email="compare-other@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=owner)
    await async_session.commit()

    same_company_response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(same_company_non_owner),
    )
    assert same_company_response.status_code == 403
    assert same_company_response.json()["detail"] == "Simulation access forbidden"

    other_company_response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(other_recruiter),
    )
    assert other_company_response.status_code == 403
    assert other_company_response.json()["detail"] == "Simulation access forbidden"
