from __future__ import annotations

import pytest

from tests.trials.routes.trials_lifecycle_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_invite_create_blocked_after_termination(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="invite-stop@test.com"
    )
    created = await _create_trial_via_api(
        async_client, async_session, auth_header_factory(talent_partner)
    )
    sim_id = created["id"]
    await _approve_trial(
        async_client, sim_id=sim_id, headers=auth_header_factory(talent_partner)
    )

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    terminate = await async_client.post(
        f"/api/trials/{sim_id}/terminate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert terminate.status_code == 200, terminate.text

    blocked = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=auth_header_factory(talent_partner),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["errorCode"] == "TRIAL_TERMINATED"
