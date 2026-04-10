from __future__ import annotations

import pytest

from tests.trials.routes.trials_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_activate_is_owner_only_and_idempotent(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(async_session, email="owner-lifecycle@test.com")
    outsider = await create_talent_partner(
        async_session, email="outsider-lifecycle@test.com"
    )
    created = await _create_trial_via_api(
        async_client, async_session, auth_header_factory(owner)
    )
    sim_id = created["id"]

    forbidden = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(outsider),
        json={"confirm": True},
    )
    assert forbidden.status_code == 403

    first = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["status"] == "active_inviting"
    assert first_body["activatedAt"] is not None

    second = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["status"] == "active_inviting"
    assert second_body["activatedAt"] == first_body["activatedAt"]
