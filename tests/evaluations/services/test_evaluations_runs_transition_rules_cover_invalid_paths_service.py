from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


@pytest.mark.asyncio
async def test_transition_rules_cover_invalid_paths(async_session):
    candidate_session = await _seed_candidate_session(async_session)

    completed_run = await eval_repo.create_run(
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
        transcript_reference="transcript:hash:completed",
        status=EVALUATION_RUN_STATUS_COMPLETED,
        started_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 3, 11, 12, 2, tzinfo=UTC),
    )
    with pytest.raises(eval_service.EvaluationRunStateError, match="invalid"):
        await eval_service.fail_run(async_session, run_id=completed_run.id)

    with pytest.raises(eval_service.EvaluationRunStateError, match="invalid"):
        eval_service._ensure_transition(
            current_status=EVALUATION_RUN_STATUS_RUNNING,
            target_status=EVALUATION_RUN_STATUS_RUNNING,
        )
    with pytest.raises(eval_service.EvaluationRunStateError, match="invalid"):
        eval_service._ensure_transition(
            current_status=EVALUATION_RUN_STATUS_FAILED,
            target_status=EVALUATION_RUN_STATUS_RUNNING,
        )
