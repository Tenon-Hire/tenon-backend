from __future__ import annotations

import pytest

from tests.trials.routes.trials_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_invite_requires_active_inviting(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="invite-state@test.com"
    )
    created = await _create_trial_via_api(
        async_client, async_session, auth_header_factory(talent_partner)
    )
    sim_id = created["id"]

    blocked = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=auth_header_factory(talent_partner),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json() == {
        "detail": "Trial is not approved for inviting.",
        "errorCode": "TRIAL_NOT_INVITABLE",
        "retryable": False,
        "details": {"status": "ready_for_review"},
    }

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    allowed = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=auth_header_factory(talent_partner),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert allowed.status_code == 200, allowed.text
