from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_api_utils import *


@pytest.mark.asyncio
async def test_invite_candidate_rejects_unowned_simulation(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="owner@example.com")
    outsider = await create_recruiter(async_session, email="outsider@example.com")
    sim, _ = await create_simulation(async_session, created_by=owner)

    res = await async_client.post(
        f"/api/simulations/{sim.id}/invite",
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
        headers=auth_header_factory(outsider),
    )
    assert res.status_code == 404
