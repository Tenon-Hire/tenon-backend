from __future__ import annotations

import pytest

from app.evaluations.repositories import (
    evaluations_repositories_evaluations_day_scores_repository as day_scores_repo,
)
from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_add_day_scores_guard_and_duplicate_existing_day(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    transient_run = EvaluationRun(
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_RUNNING,
        started_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript:hash:abcd",
    )
    with pytest.raises(ValueError, match="persisted before adding day scores"):
        await eval_repo.add_day_scores(
            async_session,
            run=transient_run,
            day_scores=_day_scores_payload(),
        )

    persisted_run = await eval_repo.create_run(
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
        transcript_reference="transcript:hash:add-day",
        status=EVALUATION_RUN_STATUS_RUNNING,
    )
    created = await eval_repo.add_day_scores(
        async_session,
        run=persisted_run,
        day_scores=[
            {
                "day_index": 1,
                "score": 90.0,
                "rubric_results_json": {"quality": 5},
                "evidence_pointers_json": [],
            }
        ],
        commit=True,
    )
    assert created[0].id is not None

    with pytest.raises(ValueError, match="already has day scores"):
        await eval_repo.add_day_scores(
            async_session,
            run=persisted_run,
            day_scores=[
                {
                    "day_index": 1,
                    "score": 91.0,
                    "rubric_results_json": {"quality": 5},
                    "evidence_pointers_json": [],
                }
            ],
        )


@pytest.mark.asyncio
async def test_add_day_scores_allow_empty_returns_empty_list(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    run = await eval_repo.create_run(
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
        transcript_reference="transcript:hash:add-day-empty",
        status=EVALUATION_RUN_STATUS_RUNNING,
    )

    created = await eval_repo.add_day_scores(
        async_session,
        run=run,
        day_scores=[],
        allow_empty=True,
        commit=False,
    )

    assert created == []


def test_normalize_day_score_payload_allow_empty_returns_empty_list():
    assert day_scores_repo.normalize_day_score_payload([], allow_empty=True) == []
