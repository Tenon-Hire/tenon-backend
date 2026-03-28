from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_api_utils import *


@pytest.mark.asyncio
async def test_list_simulations_scoped_to_owner(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(
        async_session, email="owner@example.com", name="Owner Recruiter"
    )
    other = await create_recruiter(
        async_session, email="other@example.com", name="Other Recruiter"
    )

    owned_sim, _ = await create_simulation(
        async_session, created_by=owner, title="Owner Sim"
    )
    await create_simulation(async_session, created_by=other, title="Other Sim")

    res = await async_client.get("/api/simulations", headers=auth_header_factory(owner))
    assert res.status_code == 200, res.text

    ids = {item["id"] for item in res.json()}
    assert owned_sim.id in ids
    # cross-company sim must be hidden
    assert all(item["title"] != "Other Sim" for item in res.json())
