from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *


@pytest.mark.asyncio
async def test_invite_invalid_trial_returns_404(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")

    await seed_talent_partner(
        async_session,
        email="talent_partnerA@winoe.com",
        company_name="TalentPartner A Co",
    )

    resp = await async_client.post(
        "/api/trials/999999/invite",
        headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert resp.status_code == 404
