from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_jobs_service import (
    EVALUATION_RUN_JOB_TYPE,
)
from tests.shared.factories import (
    create_candidate_session,
    create_company,
    create_job,
    create_submission,
    create_talent_partner,
    create_trial,
)


def _all_days_true(day_completion: dict[str, bool]) -> bool:
    return all(day_completion.get(str(day), False) for day in range(1, 6))


def _parse_iso_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


async def _seed_compare_candidates_scenario(async_session):
    company = await create_company(async_session, name="Compare Co")
    talent_partner = await create_talent_partner(
        async_session,
        company=company,
        email="compare-owner@test.com",
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    now = datetime.now(UTC).replace(microsecond=0)
    candidate_a = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="   ",
        invite_email="compare-a@example.com",
        status="not_started",
    )
    candidate_b = await create_candidate_session(
        async_session,
        trial=trial,
        candidate_name="Ada Lovelace",
        invite_email="compare-b@example.com",
        status="in_progress",
        started_at=now - timedelta(hours=2),
    )
    candidate_c = await create_candidate_session(
        async_session,
        trial=trial,
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
        overall_winoe_score=0.78,
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
    return talent_partner, trial, candidate_a, candidate_b, candidate_c


__all__ = [name for name in globals() if not name.startswith("__")]
