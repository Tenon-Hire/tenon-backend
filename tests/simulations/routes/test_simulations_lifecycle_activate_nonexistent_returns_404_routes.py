from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_activate_nonexistent_returns_404(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="missing-lifecycle@test.com")

    missing = await async_client.post(
        "/api/simulations/999999/activate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Simulation not found"
