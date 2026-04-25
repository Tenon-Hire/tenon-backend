from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATIONS,
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


_COMPARE_SIGNAL_TO_STORED_RECOMMENDATION = {
    "strong_signal": "strong_hire",
    "positive_signal": "hire",
    "mixed_signal": "lean_hire",
    "limited_signal": "no_hire",
}


def _stored_compare_recommendation(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in _COMPARE_SIGNAL_TO_STORED_RECOMMENDATION:
        return _COMPARE_SIGNAL_TO_STORED_RECOMMENDATION[normalized]
    if normalized in EVALUATION_RECOMMENDATIONS:
        return normalized
    raise AssertionError(f"Unsupported compare recommendation: {value}")


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
        recommendation=_stored_compare_recommendation("positive_signal"),
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


async def _create_ready_compare_run(
    async_session,
    *,
    candidate_session,
    overall_winoe_score: float,
    recommendation: str = "mixed_signal",
    generated_at: datetime | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    model_name: str = "gpt-5-evaluator",
    model_version: str = "2026-03-12",
    prompt_version: str = "prompt.v1",
    rubric_version: str = "rubric.v1",
    day2_checkpoint_sha: str = "day2-sha",
    day3_final_sha: str = "day3-sha",
    cutoff_commit_sha: str = "cutoff-sha",
    transcript_reference: str = "transcript-ref",
):
    now = datetime.now(UTC).replace(microsecond=0)
    await evaluation_repo.create_run(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name=model_name,
        model_version=model_version,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
        day2_checkpoint_sha=day2_checkpoint_sha,
        day3_final_sha=day3_final_sha,
        cutoff_commit_sha=cutoff_commit_sha,
        transcript_reference=transcript_reference,
        started_at=started_at or now - timedelta(minutes=18),
        completed_at=completed_at or now - timedelta(minutes=16),
        generated_at=generated_at or now - timedelta(minutes=15),
        overall_winoe_score=overall_winoe_score,
        recommendation=_stored_compare_recommendation(recommendation),
        commit=False,
    )


__all__ = [name for name in globals() if not name.startswith("__")]
