from __future__ import annotations

import pytest

from tests.trials.routes.trials_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_orders_candidates_and_assigns_deterministic_display_names(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session,
        email="compare-ordering@test.com",
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)

    first = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="   ",
        invite_email="order-first@example.com",
        status="not_started",
    )
    second = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="Katherine Johnson",
        invite_email="order-second@example.com",
        status="not_started",
    )
    third = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="",
        invite_email="order-third@example.com",
        status="not_started",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert [row["candidateSessionId"] for row in payload["candidates"]] == [
        first.id,
        second.id,
        third.id,
    ]
    assert [row["candidateName"] for row in payload["candidates"]] == [
        "Candidate A",
        "Katherine Johnson",
        "Candidate C",
    ]
    assert [row["candidateDisplayName"] for row in payload["candidates"]] == [
        "Candidate A",
        "Katherine Johnson",
        "Candidate C",
    ]
