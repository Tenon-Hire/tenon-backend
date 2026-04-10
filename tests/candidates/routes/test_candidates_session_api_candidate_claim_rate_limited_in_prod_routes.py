from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_candidate_claim_rate_limited_in_prod(
    async_client, async_session, monkeypatch
):
    monkeypatch.setattr(settings, "ENV", "prod")
    candidate_routes.rate_limit.limiter.reset()
    original_rule = candidate_routes.CANDIDATE_CLAIM_RATE_LIMIT
    candidate_routes.CANDIDATE_CLAIM_RATE_LIMIT = (
        candidate_routes.rate_limit.RateLimitRule(limit=1, window_seconds=60.0)
    )

    talent_partner = await create_talent_partner(
        async_session, email="claim-rate@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)

    first = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert first.status_code == 200, first.text

    second = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert second.status_code == 429

    candidate_routes.CANDIDATE_CLAIM_RATE_LIMIT = original_rule
    candidate_routes.rate_limit.limiter.reset()
