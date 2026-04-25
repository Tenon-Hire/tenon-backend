from __future__ import annotations

import pytest

from tests.trials.routes.trials_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_returns_empty_candidates_for_trial_without_sessions(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session,
        email="compare-empty-owner@test.com",
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload == {
        "trialId": trial.id,
        "cohortSize": 0,
        "state": "empty",
        "message": "No completed Winoe Reports are available for this Trial yet.",
        "candidates": [],
    }
