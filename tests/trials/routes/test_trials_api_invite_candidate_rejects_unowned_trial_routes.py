from __future__ import annotations

import pytest

from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_invite_candidate_rejects_unowned_trial(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(async_session, email="owner@example.com")
    outsider = await create_talent_partner(async_session, email="outsider@example.com")
    sim, _ = await create_trial(async_session, created_by=owner)

    res = await async_client.post(
        f"/api/trials/{sim.id}/invite",
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
        headers=auth_header_factory(outsider),
    )
    assert res.status_code == 404
