from __future__ import annotations

import pytest

from tests.trials.routes.trials_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_activate_requires_confirm_true(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(
        async_session, email="confirm-lifecycle@test.com"
    )
    created = await _create_trial_via_api(
        async_client, async_session, auth_header_factory(owner)
    )
    sim_id = created["id"]

    res = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": False},
    )
    assert res.status_code == 400
    assert res.json()["errorCode"] == "TRIAL_CONFIRMATION_REQUIRED"
