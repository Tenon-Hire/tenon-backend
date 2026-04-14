from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_invite_rate_limited_in_prod(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    monkeypatch.setattr(settings, "ENV", "prod")
    monkeypatch.setattr(settings, "SCENARIO_GENERATION_RUNTIME_MODE", "test")
    monkeypatch.setattr(settings, "CODESPACE_SPECIALIZER_RUNTIME_MODE", "test")
    sim_routes.rate_limit.limiter.reset()
    original_rule = sim_routes.INVITE_CREATE_RATE_LIMIT
    sim_routes.INVITE_CREATE_RATE_LIMIT = sim_routes.rate_limit.RateLimitRule(
        limit=1, window_seconds=60.0
    )

    await seed_talent_partner(
        async_session,
        email="talent_partner-rate@winoe.com",
        company_name="TalentPartner Rate Co",
    )

    sim_id = await _create_and_generate_trial(
        async_client, async_session, "talent_partner-rate@winoe.com"
    )

    await _approve_trial(
        async_client,
        sim_id=sim_id,
        headers={"x-dev-user-email": "talent_partner-rate@winoe.com"},
    )

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers={"x-dev-user-email": "talent_partner-rate@winoe.com"},
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    first = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers={"x-dev-user-email": "talent_partner-rate@winoe.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert first.status_code == 200, first.text

    second = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers={"x-dev-user-email": "talent_partner-rate@winoe.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert second.status_code == 429

    sim_routes.INVITE_CREATE_RATE_LIMIT = original_rule
    sim_routes.rate_limit.limiter.reset()
