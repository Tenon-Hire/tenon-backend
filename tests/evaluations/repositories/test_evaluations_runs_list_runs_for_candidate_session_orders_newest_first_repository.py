from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_list_runs_for_candidate_session_orders_newest_first(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    first_started_at = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)
    second_started_at = datetime(2026, 3, 10, 16, 0, tzinfo=UTC)

    first = await eval_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        started_at=first_started_at,
        completed_at=datetime(2026, 3, 10, 14, 5, tzinfo=UTC),
        model_name="gpt-5-evaluator",
        model_version="2026-03-10",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha-1",
        day3_final_sha="day3-sha-1",
        cutoff_commit_sha="cutoff-sha-1",
        transcript_reference="transcript:hash:first",
        metadata_json={"run": 1},
        day_scores=_day_scores_payload(),
    )
    second = await eval_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        started_at=second_started_at,
        completed_at=datetime(2026, 3, 10, 16, 7, tzinfo=UTC),
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v5",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha-2",
        day3_final_sha="day3-sha-2",
        cutoff_commit_sha="cutoff-sha-2",
        transcript_reference="transcript:hash:second",
        metadata_json={"run": 2},
        day_scores=_day_scores_payload(),
    )

    runs = await eval_repo.list_runs_for_candidate_session(
        async_session, candidate_session_id=candidate_session.id
    )
    assert [row.id for row in runs] == [second.id, first.id]
