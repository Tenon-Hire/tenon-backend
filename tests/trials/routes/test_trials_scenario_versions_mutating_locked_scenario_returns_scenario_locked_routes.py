from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_mutating_locked_scenario_returns_scenario_locked(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-mutate@test.com"
    )
    sim_id = await _create_trial(
        async_client, async_session, auth_header_factory(talent_partner)
    )

    await _approve_trial(
        async_client, sim_id=sim_id, headers=auth_header_factory(talent_partner)
    )
    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=auth_header_factory(talent_partner),
        json={"candidateName": "Locked", "inviteEmail": "locked@example.com"},
    )
    assert invite.status_code == 200, invite.text

    mutate = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/active",
        headers=auth_header_factory(talent_partner),
        json={"focusNotes": "This should fail"},
    )
    assert mutate.status_code == 409, mutate.text
    assert mutate.json() == {
        "detail": "Scenario version is locked.",
        "errorCode": "SCENARIO_LOCKED",
    }
