from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_create_run_with_day_scores_commit_false_and_query_branches(
    async_session,
):
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
    run_a = await eval_repo.create_run_with_day_scores(
        async_session,
        **base_kwargs,
        day_scores=_day_scores_payload(),
        commit=False,
    )
    run_b = await eval_repo.create_run_with_day_scores(
        async_session,
        **base_kwargs,
        started_at=datetime(2026, 3, 11, 13, 0, tzinfo=UTC),
        completed_at=datetime(2026, 3, 11, 13, 10, tzinfo=UTC),
        day_scores=_day_scores_payload(),
    )
    run_c = await eval_repo.create_run_with_day_scores(
        async_session,
        **base_kwargs,
        started_at=datetime(2026, 3, 11, 14, 0, tzinfo=UTC),
        completed_at=datetime(2026, 3, 11, 14, 5, tzinfo=UTC),
        day_scores=_day_scores_payload(),
    )

    assert run_a.id is not None
    run_a_fetched = await eval_repo.get_run_by_id(async_session, run_a.id)
    assert run_a_fetched is not None
    assert len(run_a_fetched.day_scores) == 2

    locked = await eval_repo.get_run_by_id(async_session, run_b.id, for_update=True)
    assert locked is not None

    filtered = await eval_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        offset=1,
        limit=1,
    )
    assert len(filtered) == 1
    assert filtered[0].id in {run_a.id, run_b.id, run_c.id}
