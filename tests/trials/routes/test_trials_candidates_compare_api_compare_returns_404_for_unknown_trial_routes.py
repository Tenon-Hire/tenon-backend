from __future__ import annotations

import pytest

from tests.trials.routes.trials_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_returns_404_for_unknown_trial(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session,
        email="compare-404@test.com",
    )
    await async_session.commit()

    response = await async_client.get(
        "/api/trials/999999/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Trial not found"
