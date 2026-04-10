from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_rate_limited_in_prod(
    async_client, async_session, auth_header_factory, monkeypatch
):
    monkeypatch.setattr(settings, "ENV", "prod")
    monkeypatch.setattr(settings, "SCENARIO_GENERATION_RUNTIME_MODE", "test")
    sim_routes.rate_limit.limiter.reset()
    original_rule = sim_routes.SCENARIO_REGENERATE_RATE_LIMIT
    sim_routes.SCENARIO_REGENERATE_RATE_LIMIT = sim_routes.rate_limit.RateLimitRule(
        limit=1, window_seconds=60.0
    )

    try:
        talent_partner = await create_talent_partner(
            async_session, email="scenario-regen-rate@test.com"
        )
        headers = auth_header_factory(talent_partner)
        first_sim_id = await _create_trial(async_client, async_session, headers)
        second_sim_id = await _create_trial(async_client, async_session, headers)

        activate_first = await async_client.post(
            f"/api/trials/{first_sim_id}/activate",
            headers=headers,
            json={"confirm": True},
        )
        assert activate_first.status_code == 200, activate_first.text
        activate_second = await async_client.post(
            f"/api/trials/{second_sim_id}/activate",
            headers=headers,
            json={"confirm": True},
        )
        assert activate_second.status_code == 200, activate_second.text

        first = await async_client.post(
            f"/api/trials/{first_sim_id}/scenario/regenerate",
            headers=headers,
        )
        assert first.status_code == 200, first.text

        second = await async_client.post(
            f"/api/trials/{second_sim_id}/scenario/regenerate",
            headers=headers,
        )
        assert second.status_code == 429, second.text
    finally:
        sim_routes.SCENARIO_REGENERATE_RATE_LIMIT = original_rule
        sim_routes.rate_limit.limiter.reset()
