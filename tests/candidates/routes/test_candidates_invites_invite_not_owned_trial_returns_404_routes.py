from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *


@pytest.mark.asyncio
async def test_invite_not_owned_trial_returns_404(
    async_client, async_session: AsyncSession
):
    await seed_talent_partner(
        async_session,
        email="talent_partnerA@winoe.com",
        company_name="TalentPartner A Co",
    )
    await seed_talent_partner(
        async_session,
        email="talent_partnerB@winoe.com",
        company_name="TalentPartner B Co",
    )

    sim_id = await _create_and_activate_trial(
        async_client, async_session, "talent_partnerA@winoe.com"
    )

    # TalentPartner B attempts invite -> 404 (do not leak existence)
    resp = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers={"x-dev-user-email": "talent_partnerB@winoe.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert resp.status_code == 404
