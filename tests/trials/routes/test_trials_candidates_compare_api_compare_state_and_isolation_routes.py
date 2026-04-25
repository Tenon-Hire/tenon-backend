from __future__ import annotations

import pytest

from tests.trials.routes.trials_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_returns_partial_state_for_single_ready_candidate(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session,
        email="compare-single-ready@test.com",
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="Single Ready",
        invite_email="compare-single-ready@example.com",
        status="completed",
    )
    await _create_ready_compare_run(
        async_session,
        candidate_session=candidate,
        overall_winoe_score=0.81,
        recommendation="positive_signal",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["cohortSize"] == 1
    assert payload["state"] == "partial"
    assert payload["message"] == (
        "Limited comparison — only 1 candidate completed this Trial."
    )
    assert [row["candidateSessionId"] for row in payload["candidates"]] == [
        candidate.id
    ]
    row = payload["candidates"][0]
    assert row["candidateName"] == "Single Ready"
    assert row["winoeReportStatus"] == "ready"
    assert row["overallWinoeScore"] == 0.81
    assert row["recommendation"] == "positive_signal"
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
