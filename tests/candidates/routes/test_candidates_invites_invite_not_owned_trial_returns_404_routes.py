from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


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

    sim_id = await _create_and_generate_trial(
        async_client, async_session, "talent_partnerA@winoe.com"
    )

    await _approve_trial(
        async_client,
        sim_id=sim_id,
        headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
    )

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    # TalentPartner B attempts invite -> 404 (do not leak existence)
    resp = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers={"x-dev-user-email": "talent_partnerB@winoe.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert resp.status_code == 404
