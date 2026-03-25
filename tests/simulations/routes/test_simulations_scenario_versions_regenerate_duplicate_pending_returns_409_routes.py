from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_duplicate_pending_returns_409(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-duplicate@test.com"
    )
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )
    headers = auth_header_factory(recruiter)

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    first = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert first.status_code == 200, first.text

    second = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert second.status_code == 409, second.text
    assert second.json()["errorCode"] == "SCENARIO_REGENERATION_PENDING"
