from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_create_run_with_day_scores_is_atomic(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    candidate_session_id = candidate_session.id
    scenario_version_id = candidate_session.scenario_version_id
    with pytest.raises(eval_repo.EvidencePointerValidationError):
        await eval_repo.create_run_with_day_scores(
            async_session,
            candidate_session_id=candidate_session_id,
            scenario_version_id=scenario_version_id,
            status=EVALUATION_RUN_STATUS_COMPLETED,
            model_name="gpt-5-evaluator",
            model_version="2026-03-11",
            prompt_version="prompt.v4",
            rubric_version="rubric.v2",
            day2_checkpoint_sha="day2-sha",
            day3_final_sha="day3-sha",
            cutoff_commit_sha="cutoff-sha",
            transcript_reference="transcript:hash:abcd",
            day_scores=[
                {
                    "day_index": 2,
                    "score": 90,
                    "rubric_results_json": {"delivery": 5},
                    "evidence_pointers_json": [{"kind": "commit"}],
                }
            ],
        )
    await async_session.rollback()

    runs = await eval_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session_id,
    )
    assert runs == []
