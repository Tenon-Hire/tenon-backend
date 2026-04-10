from __future__ import annotations

import pytest

from tests.trials.routes.trials_candidates_compare_api_utils import *


@pytest.mark.asyncio
async def test_compare_updated_at_uses_fit_then_session_activity_precedence(
    async_client, async_session, auth_header_factory
):
    company = await create_company(async_session, name="Compare UpdatedAt Co")
    talent_partner = await create_talent_partner(
        async_session,
        company=company,
        email="compare-updated-at@test.com",
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    base = datetime(2026, 3, 16, 18, 0, tzinfo=UTC)

    fit_candidate = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="Fit Candidate",
        invite_email="fit-candidate@example.com",
        status="in_progress",
        started_at=base - timedelta(hours=4),
    )
    fit_candidate.invite_email_last_attempt_at = base - timedelta(minutes=5)

    session_candidate = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="Session Candidate",
        invite_email="session-candidate@example.com",
        status="in_progress",
        started_at=base - timedelta(hours=2),
        schedule_locked_at=base - timedelta(minutes=40),
    )

    fit_generated_at = base - timedelta(minutes=10)
    await evaluation_repo.create_run(
        async_session,
        candidate_session_id=fit_candidate.id,
        scenario_version_id=fit_candidate.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v1",
        rubric_version="rubric.v1",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript-ref",
        started_at=base - timedelta(minutes=14),
        completed_at=base - timedelta(minutes=12),
        generated_at=fit_generated_at,
        overall_winoe_score=0.71,
        recommendation="lean_hire",
        commit=False,
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    rows_by_id = {row["candidateSessionId"]: row for row in payload["candidates"]}

    fit_row = rows_by_id[fit_candidate.id]
    session_row = rows_by_id[session_candidate.id]

    assert _parse_iso_utc(fit_row["updatedAt"]) == fit_generated_at
    assert _parse_iso_utc(session_row["updatedAt"]) == base - timedelta(minutes=40)
