from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.shared.database.shared_database_models_model import WinoeReport
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_invites_list_serializes_canonical_status_and_derived_fields(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session,
        email="qa180.tp@example.com",
        company_name="QA180 Co",
        name="QA Talent Partner",
    )

    report_trial, _ = await create_trial(
        async_session,
        created_by=talent_partner,
        title="QA180: Report Ready Trial",
    )
    report_session = await create_candidate_session(
        async_session,
        trial=report_trial,
        invite_email="qa180.candidate@example.com",
        candidate_name="Report Ready Candidate",
        status="in_progress",
    )
    async_session.add(
        WinoeReport(
            candidate_session_id=report_session.id,
            generated_at=datetime.now(UTC),
        )
    )

    terminated_trial, _ = await create_trial(
        async_session,
        created_by=talent_partner,
        title="QA180: Terminated Trial",
    )
    terminated_trial.status = "terminated"
    terminated_trial.terminated_at = datetime.now(UTC)
    terminated_session = await create_candidate_session(
        async_session,
        trial=terminated_trial,
        invite_email="qa180.candidate@example.com",
        candidate_name="Terminated Candidate",
        status="not_started",
    )

    await async_session.commit()

    response = await async_client.get(
        "/api/candidate/invites?includeTerminated=true",
        headers={"Authorization": "Bearer candidate:qa180.candidate@example.com"},
    )

    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) == 2

    by_trial_id = {item["trialId"]: item for item in items}

    report_row = by_trial_id[report_trial.id]
    assert report_row["candidateSessionId"] == report_session.id
    assert report_row["status"] == "in_progress"
    assert report_row["reportReady"] is True
    assert report_row["hasReport"] is True
    assert report_row["terminatedAt"] is None
    assert report_row["isTerminated"] is False

    terminated_row = by_trial_id[terminated_trial.id]
    assert terminated_row["candidateSessionId"] == terminated_session.id
    assert terminated_row["status"] == "not_started"
    assert terminated_row["reportReady"] is False
    assert terminated_row["hasReport"] is False
    assert terminated_row["terminatedAt"] is not None
    assert terminated_row["isTerminated"] is True
