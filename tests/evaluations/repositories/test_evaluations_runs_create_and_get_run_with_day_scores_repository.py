from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_create_and_get_run_with_day_scores(async_session):
    candidate_session = await _seed_candidate_session(async_session)

    run = await eval_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript:hash:abcd",
        metadata_json={"jobId": "job_123"},
        day_scores=_day_scores_payload(),
    )

    fetched = await eval_repo.get_run_by_id(async_session, run.id)
    assert fetched is not None
    assert fetched.id == run.id
    assert fetched.candidate_session_id == candidate_session.id
    assert fetched.scenario_version_id == candidate_session.scenario_version_id
    assert fetched.status == EVALUATION_RUN_STATUS_COMPLETED
    assert fetched.day2_checkpoint_sha == "day2-sha"
    assert fetched.day3_final_sha == "day3-sha"
    assert fetched.cutoff_commit_sha == "cutoff-sha"
    assert fetched.transcript_reference == "transcript:hash:abcd"
    assert len(fetched.day_scores) == 2
    assert fetched.day_scores[0].day_index == 1
    assert fetched.day_scores[1].day_index == 4
    assert fetched.day_scores[0].evidence_pointers_json[0]["kind"] == "commit"
    assert fetched.day_scores[1].evidence_pointers_json[0]["kind"] == "transcript"
