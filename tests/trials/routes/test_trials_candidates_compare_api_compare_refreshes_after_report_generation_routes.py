from __future__ import annotations

import pytest

from tests.trials.routes.trials_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_refreshes_after_report_generation(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session,
        email="compare-refresh@test.com",
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="Refresh Candidate",
        invite_email="compare-refresh@example.com",
        status="completed",
    )
    await async_session.commit()

    first_response = await async_client.get(
        f"/api/trials/{trial.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert first_response.status_code == 200, first_response.text
    first_payload = first_response.json()
    assert first_payload["cohortSize"] == 0
    assert first_payload["state"] == "empty"
    assert first_payload["candidates"] == []

    await _create_ready_compare_run(
        async_session,
        candidate_session=candidate,
        overall_winoe_score=0.88,
        recommendation="strong_signal",
    )
    await async_session.commit()

    second_response = await async_client.get(
        f"/api/trials/{trial.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert second_response.status_code == 200, second_response.text
    second_payload = second_response.json()
    assert second_payload["cohortSize"] == 1
    assert second_payload["state"] == "partial"
    assert second_payload["message"] == (
        "Limited comparison — only 1 candidate completed this Trial."
    )
    assert [row["candidateSessionId"] for row in second_payload["candidates"]] == [
        candidate.id
    ]
    row = second_payload["candidates"][0]
    assert row["overallWinoeScore"] == 0.88
    assert row["recommendation"] == "strong_signal"
    assert row["recommendation"] not in {
        "hire",
        "lean_hire",
        "strong_hire",
        "no_hire",
        "reject",
        "pass",
        "fail",
        "Winoe recommends",
    }
