from __future__ import annotations

import pytest

from app.shared.database.shared_database_models_model import Company
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
    await _create_ready_compare_run(
        async_session,
        candidate_session=candidate_b,
        overall_winoe_score=0.64,
        recommendation="mixed_signal",
    )
    trial_b, tasks_b = await create_trial(
        async_session,
        created_by=talent_partner,
        title="Unrelated Trial",
    )
    candidate_d = await create_candidate_session(
        async_session,
        trial=trial_b,
        candidate_name="Candidate B",
        invite_email="compare-b-unrelated@example.com",
        status="completed",
        completed_at=datetime.now(UTC).replace(microsecond=0),
    )
    for index, task in enumerate(tasks_b):
        await create_submission(
            async_session,
            candidate_session=candidate_d,
            task=task,
            submitted_at=datetime.now(UTC).replace(microsecond=0)
            - timedelta(minutes=index),
            content_text=f"trial-b day{task.day_index}",
        )
    await evaluation_repo.create_run(
        async_session,
        candidate_session_id=candidate_d.id,
        scenario_version_id=candidate_d.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v1",
        rubric_version="rubric.v1",
        day2_checkpoint_sha="day2-sha-b",
        day3_final_sha="day3-sha-b",
        cutoff_commit_sha="cutoff-sha-b",
        transcript_reference="transcript-ref-b",
        started_at=datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=10),
        completed_at=datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=8),
        generated_at=datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=7),
        overall_winoe_score=0.95,
        recommendation="positive_signal",
        commit=False,
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    await create_job(
        async_session,
        company=company,
        candidate_session=candidate_d,
        job_type=EVALUATION_RUN_JOB_TYPE,
        status="queued",
        idempotency_key="compare-job-candidate-d",
    )
    other_company = await create_company(async_session, name="Other Compare Co")
    other_partner = await create_talent_partner(
        async_session,
        company=other_company,
        email="compare-other-company@test.com",
    )
    other_trial, other_tasks = await create_trial(
        async_session,
        created_by=other_partner,
        title="Other Company Trial",
    )
    other_candidate = await create_candidate_session(
        async_session,
        trial=other_trial,
        candidate_name="Other Company Ready",
        invite_email="compare-other-company@example.com",
        status="completed",
        completed_at=datetime.now(UTC).replace(microsecond=0),
    )
    for index, task in enumerate(other_tasks):
        await create_submission(
            async_session,
            candidate_session=other_candidate,
            task=task,
            submitted_at=datetime.now(UTC).replace(microsecond=0)
            - timedelta(minutes=index + 10),
            content_text=f"other-company day{task.day_index}",
        )
    await evaluation_repo.create_run(
        async_session,
        candidate_session_id=other_candidate.id,
        scenario_version_id=other_candidate.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v1",
        rubric_version="rubric.v1",
        day2_checkpoint_sha="day2-sha-other",
        day3_final_sha="day3-sha-other",
        cutoff_commit_sha="cutoff-sha-other",
        transcript_reference="transcript-ref-other",
        started_at=datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=12),
        completed_at=datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=11),
        generated_at=datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=10),
        overall_winoe_score=0.67,
        recommendation="mixed_signal",
        commit=False,
    )
    await create_job(
        async_session,
        company=other_company,
        candidate_session=other_candidate,
        job_type=EVALUATION_RUN_JOB_TYPE,
        status="queued",
        idempotency_key="compare-job-other-candidate",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["trialId"] == trial.id
    assert payload["cohortSize"] == 2
    assert payload["state"] == "partial"
    assert payload["message"] == (
        "Limited comparison — only 2 candidates completed this Trial."
    )
    assert [row["candidateSessionId"] for row in payload["candidates"]] == [
        candidate_b.id,
        candidate_c.id,
    ]
    assert all(
        row["candidateSessionId"] not in {candidate_a.id, candidate_d.id}
        for row in payload["candidates"]
    )
    assert other_candidate.id not in {
        row["candidateSessionId"] for row in payload["candidates"]
    }

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
    assert first["candidateName"] == "Ada Lovelace"
    assert first["candidateDisplayName"] == "Ada Lovelace"
    assert first["status"] == "evaluated"
    assert first["winoeReportStatus"] == "ready"
    assert first["overallWinoeScore"] == 0.64
    assert first["recommendation"] == "mixed_signal"
    assert first["recommendation"] not in {
        "hire",
        "lean_hire",
        "strong_hire",
        "no_hire",
        "reject",
        "pass",
        "fail",
        "Winoe recommends",
    }
    assert first["dayCompletion"] == {
        "1": True,
        "2": False,
        "3": False,
        "4": False,
        "5": False,
    }
    assert isinstance(first["updatedAt"], str)

    second = payload["candidates"][1]
    assert second["candidateName"] == "Grace Hopper"
    assert second["candidateDisplayName"] == "Grace Hopper"
    assert second["status"] == "evaluated"
    assert second["winoeReportStatus"] == "ready"
    assert second["overallWinoeScore"] == 0.78
    assert second["recommendation"] == "positive_signal"
    assert second["recommendation"] not in {
        "hire",
        "lean_hire",
        "strong_hire",
        "no_hire",
        "reject",
        "pass",
        "fail",
        "Winoe recommends",
    }
    assert _all_days_true(second["dayCompletion"]) is True
    assert isinstance(second["updatedAt"], str)

    trial_b_response = await async_client.get(
        f"/api/trials/{trial_b.id}/candidates/compare",
        headers=auth_header_factory(talent_partner),
    )
    assert trial_b_response.status_code == 200, trial_b_response.text
    trial_b_payload = trial_b_response.json()
    assert trial_b_payload["trialId"] == trial_b.id
    assert trial_b_payload["cohortSize"] == 1
    assert trial_b_payload["state"] == "partial"
    assert trial_b_payload["message"] == (
        "Limited comparison — only 1 candidate completed this Trial."
    )
    assert [row["candidateSessionId"] for row in trial_b_payload["candidates"]] == [
        candidate_d.id,
    ]
    assert all(
        row["candidateSessionId"]
        not in {candidate_a.id, candidate_b.id, candidate_c.id}
        for row in trial_b_payload["candidates"]
    )
    assert trial_b_payload["candidates"][0]["recommendation"] == "positive_signal"
    assert trial_b_payload["candidates"][0]["recommendation"] not in {
        "hire",
        "reject",
        "pass",
        "fail",
    }
