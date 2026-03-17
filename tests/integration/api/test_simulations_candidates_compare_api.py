from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.repositories.evaluations import repository as evaluation_repo
from app.repositories.evaluations.models import EVALUATION_RUN_STATUS_COMPLETED
from app.services.evaluations.fit_profile_jobs import EVALUATION_RUN_JOB_TYPE
from tests.factories import (
    create_candidate_session,
    create_company,
    create_job,
    create_recruiter,
    create_simulation,
    create_submission,
)


def _all_days_true(day_completion: dict[str, bool]) -> bool:
    return all(day_completion.get(str(day), False) for day in range(1, 6))


def _parse_iso_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


@pytest.mark.asyncio
async def test_compare_returns_empty_candidates_for_simulation_without_sessions(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session,
        email="compare-empty-owner@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    await async_session.commit()

    response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(recruiter),
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"simulationId": simulation.id, "candidates": []}


@pytest.mark.asyncio
async def test_compare_returns_summaries_with_fit_statuses_and_nullable_fields(
    async_client, async_session, auth_header_factory
):
    company = await create_company(async_session, name="Compare Co")
    recruiter = await create_recruiter(
        async_session,
        company=company,
        email="compare-owner@test.com",
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)

    now = datetime.now(UTC).replace(microsecond=0)
    candidate_a = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="   ",
        invite_email="compare-a@example.com",
        status="not_started",
    )
    candidate_b = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="Ada Lovelace",
        invite_email="compare-b@example.com",
        status="in_progress",
        started_at=now - timedelta(hours=2),
    )
    candidate_c = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="Grace Hopper",
        invite_email="compare-c@example.com",
        status="completed",
        started_at=now - timedelta(hours=5),
        completed_at=now - timedelta(hours=1),
    )

    await create_submission(
        async_session,
        candidate_session=candidate_b,
        task=tasks[0],
        submitted_at=now - timedelta(minutes=45),
        content_text="day1 design",
    )

    for index, task in enumerate(tasks):
        await create_submission(
            async_session,
            candidate_session=candidate_c,
            task=task,
            submitted_at=now - timedelta(minutes=(20 - index)),
            content_text=f"day{task.day_index} submission",
        )

    await evaluation_repo.create_run(
        async_session,
        candidate_session_id=candidate_c.id,
        scenario_version_id=candidate_c.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v1",
        rubric_version="rubric.v1",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript-ref",
        started_at=now - timedelta(minutes=18),
        completed_at=now - timedelta(minutes=16),
        generated_at=now - timedelta(minutes=15),
        overall_fit_score=0.78,
        recommendation="hire",
        commit=False,
    )
    await create_job(
        async_session,
        company=company,
        candidate_session=candidate_b,
        job_type=EVALUATION_RUN_JOB_TYPE,
        status="queued",
        idempotency_key="compare-job-candidate-b",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(recruiter),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["simulationId"] == simulation.id
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
        "fitProfileStatus",
        "overallFitScore",
        "recommendation",
        "dayCompletion",
        "updatedAt",
    }
    assert first["candidateName"] == "Candidate A"
    assert first["candidateDisplayName"] == "Candidate A"
    assert first["status"] == "scheduled"
    assert first["fitProfileStatus"] == "none"
    assert first["overallFitScore"] is None
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
    assert second["fitProfileStatus"] == "generating"
    assert second["overallFitScore"] is None
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
    assert third["fitProfileStatus"] == "ready"
    assert third["overallFitScore"] == 0.78
    assert third["recommendation"] == "hire"
    assert _all_days_true(third["dayCompletion"]) is True
    assert isinstance(third["updatedAt"], str)


@pytest.mark.asyncio
async def test_compare_returns_404_for_unknown_simulation(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session,
        email="compare-404@test.com",
    )
    await async_session.commit()

    response = await async_client.get(
        "/api/simulations/999999/candidates/compare",
        headers=auth_header_factory(recruiter),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Simulation not found"


@pytest.mark.asyncio
async def test_compare_returns_403_for_forbidden_company_or_scope(
    async_client, async_session, auth_header_factory
):
    owner_company = await create_company(async_session, name="Owner Compare Co")
    owner = await create_recruiter(
        async_session,
        company=owner_company,
        email="compare-owner-forbidden@test.com",
    )
    same_company_non_owner = await create_recruiter(
        async_session,
        company=owner_company,
        email="compare-peer@test.com",
    )
    other_company = await create_company(async_session, name="Other Compare Co")
    other_recruiter = await create_recruiter(
        async_session,
        company=other_company,
        email="compare-other@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=owner)
    await async_session.commit()

    same_company_response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(same_company_non_owner),
    )
    assert same_company_response.status_code == 403
    assert same_company_response.json()["detail"] == "Simulation access forbidden"

    other_company_response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(other_recruiter),
    )
    assert other_company_response.status_code == 403
    assert other_company_response.json()["detail"] == "Simulation access forbidden"


@pytest.mark.asyncio
async def test_compare_orders_candidates_and_assigns_deterministic_display_names(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session,
        email="compare-ordering@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)

    first = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="   ",
        invite_email="order-first@example.com",
        status="not_started",
    )
    second = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="Katherine Johnson",
        invite_email="order-second@example.com",
        status="not_started",
    )
    third = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="",
        invite_email="order-third@example.com",
        status="not_started",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(recruiter),
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


@pytest.mark.asyncio
async def test_compare_updated_at_uses_fit_then_session_activity_precedence(
    async_client, async_session, auth_header_factory
):
    company = await create_company(async_session, name="Compare UpdatedAt Co")
    recruiter = await create_recruiter(
        async_session,
        company=company,
        email="compare-updated-at@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    base = datetime(2026, 3, 16, 18, 0, tzinfo=UTC)

    fit_candidate = await create_candidate_session(
        async_session,
        simulation=simulation,
        candidate_name="Fit Candidate",
        invite_email="fit-candidate@example.com",
        status="in_progress",
        started_at=base - timedelta(hours=4),
    )
    fit_candidate.invite_email_last_attempt_at = base - timedelta(minutes=5)

    session_candidate = await create_candidate_session(
        async_session,
        simulation=simulation,
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
        overall_fit_score=0.71,
        recommendation="lean_hire",
        commit=False,
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/simulations/{simulation.id}/candidates/compare",
        headers=auth_header_factory(recruiter),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    rows_by_id = {row["candidateSessionId"]: row for row in payload["candidates"]}

    fit_row = rows_by_id[fit_candidate.id]
    session_row = rows_by_id[session_candidate.id]

    assert _parse_iso_utc(fit_row["updatedAt"]) == fit_generated_at
    assert _parse_iso_utc(session_row["updatedAt"]) == base - timedelta(minutes=40)
