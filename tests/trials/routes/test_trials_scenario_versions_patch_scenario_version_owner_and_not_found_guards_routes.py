from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_owner_and_not_found_guards(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(
        async_session, email="scenario-patch-owner-api@test.com"
    )
    outsider = await create_talent_partner(
        async_session, email="scenario-patch-outsider-api@test.com"
    )
    owner_headers = auth_header_factory(owner)
    sim_id = await _create_trial(async_client, async_session, owner_headers)

    detail = await async_client.get(f"/api/trials/{sim_id}", headers=owner_headers)
    assert detail.status_code == 200, detail.text
    scenario_version_id = detail.json()["activeScenarioVersionId"]
    assert scenario_version_id is not None

    forbidden = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=auth_header_factory(outsider),
        json={"notes": "forbidden"},
    )
    assert forbidden.status_code == 403, forbidden.text

    missing_sim = await async_client.patch(
        "/api/trials/999999/scenario/999999",
        headers=owner_headers,
        json={"notes": "missing"},
    )
    assert missing_sim.status_code == 404, missing_sim.text

    missing_version = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/999999",
        headers=owner_headers,
        json={"notes": "missing version"},
    )
    assert missing_version.status_code == 404, missing_version.text
