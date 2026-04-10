from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_duplicate_pending_returns_409(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-regen-duplicate@test.com"
    )
    sim_id = await _create_trial(
        async_client, async_session, auth_header_factory(talent_partner)
    )
    headers = auth_header_factory(talent_partner)

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    first = await async_client.post(
        f"/api/trials/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert first.status_code == 200, first.text

    second = await async_client.post(
        f"/api/trials/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert second.status_code == 409, second.text
    assert second.json()["errorCode"] == "SCENARIO_REGENERATION_PENDING"
