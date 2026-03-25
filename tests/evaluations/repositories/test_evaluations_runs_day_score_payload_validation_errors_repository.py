from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_day_score_cases_utils import (
    DAY_SCORE_PAYLOAD_ERROR_CASES,
)
from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_day_score_payload_validation_errors(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    base_kwargs = {
        "candidate_session_id": candidate_session.id,
        "scenario_version_id": candidate_session.scenario_version_id,
        "status": EVALUATION_RUN_STATUS_COMPLETED,
        "model_name": "gpt-5-evaluator",
        "model_version": "2026-03-11",
        "prompt_version": "prompt.v4",
        "rubric_version": "rubric.v2",
        "day2_checkpoint_sha": "day2-sha",
        "day3_final_sha": "day3-sha",
        "cutoff_commit_sha": "cutoff-sha",
        "transcript_reference": "transcript:hash:abcd",
    }

    for payload, error_type, match in DAY_SCORE_PAYLOAD_ERROR_CASES:
        with pytest.raises(error_type, match=match):
            await eval_repo.create_run_with_day_scores(
                async_session,
                **base_kwargs,
                day_scores=payload,  # type: ignore[arg-type]
            )
        await async_session.rollback()
