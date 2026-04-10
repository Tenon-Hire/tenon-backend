from __future__ import annotations

import pytest

from tests.trials.routes.trials_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_returns_summaries_with_winoe_report_statuses_and_nullable_fields(
    async_client, async_session, auth_header_factory
):
    (
        talent_partner,
        trial,
        candidate_a,
        candidate_b,
        candidate_c,
    ) = await _seed_compare_candidates_scenario(async_session)

    response = await async_client.get(
        f"/api/trials/{trial.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["trialId"] == trial.id
    assert [row["candidateSessionId"] for row in payload["candidates"]] == [
        candidate_a.id,
        candidate_b.id,
        candidate_c.id,
    ]

    first = payload["candidates"][0]
    assert set(first.keys()) == {
        "candidateSessionId",
        "candidateName",
        "candidateDisplayName",
        "status",
        "winoeReportStatus",
        "overallWinoeScore",
        "recommendation",
        "dayCompletion",
        "updatedAt",
    }
    assert first["candidateName"] == "Candidate A"
    assert first["candidateDisplayName"] == "Candidate A"
    assert first["status"] == "scheduled"
    assert first["winoeReportStatus"] == "none"
    assert first["overallWinoeScore"] is None
    assert first["recommendation"] is None
    assert first["dayCompletion"] == {
        "1": False,
        "2": False,
        "3": False,
        "4": False,
        "5": False,
    }
    assert isinstance(first["updatedAt"], str)

    second = payload["candidates"][1]
    assert second["candidateName"] == "Ada Lovelace"
    assert second["candidateDisplayName"] == "Ada Lovelace"
    assert second["status"] == "in_progress"
    assert second["winoeReportStatus"] == "generating"
    assert second["overallWinoeScore"] is None
    assert second["recommendation"] is None
    assert second["dayCompletion"] == {
        "1": True,
        "2": False,
        "3": False,
        "4": False,
        "5": False,
    }
    assert isinstance(second["updatedAt"], str)

    third = payload["candidates"][2]
    assert third["candidateName"] == "Grace Hopper"
    assert third["candidateDisplayName"] == "Grace Hopper"
    assert third["status"] == "evaluated"
    assert third["winoeReportStatus"] == "ready"
    assert third["overallWinoeScore"] == 0.78
    assert third["recommendation"] == "hire"
    assert _all_days_true(third["dayCompletion"]) is True
    assert isinstance(third["updatedAt"], str)
