from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_create_run_duplicate_non_null_job_id_raises_integrity_error(
    async_session,
):
    candidate_session = await _seed_candidate_session(async_session)
    candidate_session_id = candidate_session.id
    scenario_version_id = candidate_session.scenario_version_id
    duplicate_job_id = "job-dup-1"

    await eval_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=candidate_session_id,
        scenario_version_id=scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v6",
        rubric_version="rubric.v3",
        day2_checkpoint_sha="day2-sha-a",
        day3_final_sha="day3-sha-a",
        cutoff_commit_sha="cutoff-sha-a",
        transcript_reference="transcript:job:a",
        job_id=duplicate_job_id,
        day_scores=_day_scores_payload(),
    )

    with pytest.raises(IntegrityError):
        await eval_repo.create_run_with_day_scores(
            async_session,
            candidate_session_id=candidate_session_id,
            scenario_version_id=scenario_version_id,
            status=EVALUATION_RUN_STATUS_COMPLETED,
            model_name="gpt-5-evaluator",
            model_version="2026-03-12",
            prompt_version="prompt.v6",
            rubric_version="rubric.v3",
            day2_checkpoint_sha="day2-sha-b",
            day3_final_sha="day3-sha-b",
            cutoff_commit_sha="cutoff-sha-b",
            transcript_reference="transcript:job:b",
            job_id=duplicate_job_id,
            day_scores=_day_scores_payload(),
        )
    await async_session.rollback()

    runs = await eval_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session_id,
    )
    assert len(runs) == 1
    assert runs[0].job_id == duplicate_job_id
