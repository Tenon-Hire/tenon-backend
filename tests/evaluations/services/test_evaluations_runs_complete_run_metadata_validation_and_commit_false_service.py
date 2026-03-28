from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


@pytest.mark.asyncio
async def test_complete_run_metadata_validation_and_commit_false(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    candidate_session_id = candidate_session.id
    scenario_version_id = candidate_session.scenario_version_id
    started = await eval_service.start_run(
        async_session,
        candidate_session_id=candidate_session_id,
        scenario_version_id=scenario_version_id,
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript:hash:abcd",
    )

    with pytest.raises(
        eval_service.EvaluationRunStateError, match="metadata_json must be an object"
    ):
        await eval_service.complete_run(
            async_session,
            run_id=started.id,
            day_scores=_day_scores_payload(),
            metadata_json=["invalid"],  # type: ignore[arg-type]
        )
    await async_session.rollback()

    started = await eval_service.start_run(
        async_session,
        candidate_session_id=candidate_session_id,
        scenario_version_id=scenario_version_id,
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript:hash:efgh",
    )
    completed = await eval_service.complete_run(
        async_session,
        run_id=started.id,
        day_scores=_day_scores_payload(),
        metadata_json={"job_id": "job_002"},
        commit=False,
    )
    assert completed.status == EVALUATION_RUN_STATUS_COMPLETED
    assert completed.metadata_json is not None
    assert completed.metadata_json["job_id"] == "job_002"
