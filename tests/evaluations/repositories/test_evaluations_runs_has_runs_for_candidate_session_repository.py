from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_has_runs_for_candidate_session(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    assert (
        await eval_repo.has_runs_for_candidate_session(
            async_session, candidate_session.id
        )
        is False
    )

    await eval_repo.create_run_with_day_scores(
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
        day_scores=_day_scores_payload(),
    )
    assert (
        await eval_repo.has_runs_for_candidate_session(
            async_session, candidate_session.id
        )
        is True
    )
