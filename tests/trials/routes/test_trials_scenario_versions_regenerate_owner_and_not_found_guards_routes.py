from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_owner_and_not_found_guards(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(async_session, email="scenario-owner@test.com")
    outsider = await create_talent_partner(
        async_session, email="scenario-outsider@test.com"
    )
    sim_id = await _create_trial(
        async_client, async_session, auth_header_factory(owner)
    )

    forbidden = await async_client.post(
        f"/api/trials/{sim_id}/scenario/regenerate",
        headers=auth_header_factory(outsider),
    )
    assert forbidden.status_code == 403, forbidden.text

    missing = await async_client.post(
        "/api/trials/999999/scenario/regenerate",
        headers=auth_header_factory(owner),
    )
    assert missing.status_code == 404, missing.text
