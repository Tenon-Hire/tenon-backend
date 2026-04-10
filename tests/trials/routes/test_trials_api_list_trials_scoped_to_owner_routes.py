from __future__ import annotations

import pytest

from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_list_trials_scoped_to_owner(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(
        async_session, email="owner@example.com", name="Owner TalentPartner"
    )
    other = await create_talent_partner(
        async_session, email="other@example.com", name="Other TalentPartner"
    )

    owned_sim, _ = await create_trial(
        async_session, created_by=owner, title="Owner Sim"
    )
    await create_trial(async_session, created_by=other, title="Other Sim")

    res = await async_client.get("/api/trials", headers=auth_header_factory(owner))
    assert res.status_code == 200, res.text

    ids = {item["id"] for item in res.json()}
    assert owned_sim.id in ids
    # cross-company sim must be hidden
    assert all(item["title"] != "Other Sim" for item in res.json())
