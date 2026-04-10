from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_get_run_by_job_id_filters_by_session_and_for_update(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    talent_partner = await create_talent_partner(
        async_session, email="eval-repo-jobid@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    other_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
    )
    await async_session.commit()

    first_job_id = "job-lookup-1"
    first = await eval_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v6",
        rubric_version="rubric.v3",
        day2_checkpoint_sha="day2-sha-a",
        day3_final_sha="day3-sha-a",
        cutoff_commit_sha="cutoff-sha-a",
        transcript_reference="transcript:job:a",
        job_id=first_job_id,
        day_scores=_day_scores_payload(),
    )
    second_job_id = "job-lookup-2"
    await eval_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=other_session.id,
        scenario_version_id=other_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v6",
        rubric_version="rubric.v3",
        day2_checkpoint_sha="day2-sha-b",
        day3_final_sha="day3-sha-b",
        cutoff_commit_sha="cutoff-sha-b",
        transcript_reference="transcript:job:b",
        job_id=second_job_id,
        day_scores=_day_scores_payload(),
    )

    any_run = await eval_repo.get_run_by_job_id(
        async_session,
        job_id=first_job_id,
        for_update=True,
    )
    assert any_run is not None
    assert any_run.id == first.id

    only_first_session = await eval_repo.get_run_by_job_id(
        async_session,
        job_id=first_job_id,
        candidate_session_id=candidate_session.id,
    )
    assert only_first_session is not None
    assert only_first_session.candidate_session_id == candidate_session.id

    not_in_other_session = await eval_repo.get_run_by_job_id(
        async_session,
        job_id=first_job_id,
        candidate_session_id=other_session.id,
    )
    assert not_in_other_session is None

    with pytest.raises(ValueError, match="job_id must be a non-empty string"):
        await eval_repo.get_run_by_job_id(async_session, job_id=" ")
