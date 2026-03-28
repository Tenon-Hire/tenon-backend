from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


@pytest.mark.asyncio
async def test_fail_run_sets_failed_and_blocks_future_transitions(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    started = await eval_service.start_run(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript:hash:abcd",
    )

    failed = await eval_service.fail_run(
        async_session,
        run_id=started.id,
        error_message="Model timeout",
        metadata_json={"jobId": "job_999"},
    )
    assert failed.status == "failed"
    assert failed.completed_at is not None
    assert failed.metadata_json is not None
    assert failed.metadata_json["error"] == "Model timeout"
    assert failed.metadata_json["jobId"] == "job_999"

    with pytest.raises(eval_service.EvaluationRunStateError, match="invalid"):
        await eval_service.complete_run(
            async_session,
            run_id=failed.id,
            day_scores=_day_scores_payload(),
        )
