from __future__ import annotations

import pytest

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_SUCCEEDED,
)
from tests.evaluations.routes.evaluations_winoe_report_api_utils import *


@pytest.mark.asyncio
async def test_winoe_report_disabled_day_multiple_runs_and_cutoff_immutability(
    async_client,
    async_session,
    auth_header_factory,
):
    talent_partner, candidate_session = await _seed_completed_candidate_session(
        async_session,
        ai_eval_enabled_by_day={"4": False},
    )

    first_generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report/generate",
        headers=auth_header_factory(talent_partner),
    )
    assert first_generate.status_code == 202, first_generate.text
    first_job_id = first_generate.json()["jobId"]
    assert (
        await _run_worker_once(async_session, worker_id="winoe-report-worker-first")
        is True
    )

    day2_submission = (
        await async_session.execute(
            select(Submission)
            .join(Task, Task.id == Submission.task_id)
            .where(
                Submission.candidate_session_id == candidate_session.id,
                Task.day_index == 2,
            )
        )
    ).scalar_one()
    day2_submission.commit_sha = "mutated-latest-day2-sha"
    day2_submission.checkpoint_sha = "mutated-latest-day2-checkpoint"
    await async_session.commit()

    second_generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report/generate",
        headers=auth_header_factory(talent_partner),
    )
    assert second_generate.status_code == 202, second_generate.text
    second_job_id = second_generate.json()["jobId"]
    assert second_job_id != first_job_id
    assert (
        await _run_worker_once(async_session, worker_id="winoe-report-worker-second")
        is True
    )

    runs = await evaluation_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    assert len(runs) == 2
    assert runs[0].id != runs[1].id

    for run in runs:
        assert run.day2_checkpoint_sha == "cutoff-day2-fixed"
        assert run.day3_final_sha == "cutoff-day3-fixed"
        assert run.status == EVALUATION_RUN_STATUS_COMPLETED
        assert run.job_id in {first_job_id, second_job_id}
        assert run.error_code is None
        assert run.metadata_json is not None
        assert run.metadata_json.get("disabledDayIndexes") == [4]
        assert 4 not in [row.day_index for row in run.day_scores]

    first_job = await async_session.get(Job, first_job_id)
    second_job = await async_session.get(Job, second_job_id)
    assert first_job is not None
    assert second_job is not None
    assert first_job.status == JOB_STATUS_SUCCEEDED
    assert second_job.status == JOB_STATUS_SUCCEEDED
    assert first_job.last_error is None
    assert second_job.last_error is None
    assert (
        first_job.payload_json["basisFingerprint"]
        != second_job.payload_json["basisFingerprint"]
    )

    fetch = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report",
        headers=auth_header_factory(talent_partner),
    )
    assert fetch.status_code == 200, fetch.text
    body = fetch.json()
    assert body["status"] == "ready"
    day_scores = body["report"]["dayScores"]
    day4_entry = next(day for day in day_scores if day["dayIndex"] == 4)
    assert day4_entry["status"] == "human_review_required"
    assert day4_entry["reason"] == "ai_eval_disabled_for_day"
    assert day4_entry["score"] is None
    scored_days = [day for day in day_scores if day["status"] == "scored"]
    assert scored_days
    expected_overall = round(
        sum(float(day["score"]) for day in scored_days) / len(scored_days),
        4,
    )
    assert body["report"]["overallWinoeScore"] == expected_overall
