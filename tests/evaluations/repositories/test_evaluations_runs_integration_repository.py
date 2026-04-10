from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.evaluations.repositories import repository as eval_repo
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


async def _seed_candidate_session(async_session):
    talent_partner = await create_talent_partner(
        async_session,
        email="eval-integration@test.com",
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
    )
    await async_session.commit()
    return candidate_session


def _day_scores(day_index: int, score: float, ref: str) -> list[dict]:
    return [
        {
            "day_index": day_index,
            "score": score,
            "rubric_results_json": {"delivery": score},
            "evidence_pointers_json": [
                {
                    "kind": "commit",
                    "ref": ref,
                    "url": f"https://github.com/acme/repo/commit/{ref}",
                }
            ],
        }
    ]


@pytest.mark.asyncio
async def test_db_backed_evaluation_reruns_persist_without_overwrite(async_session):
    candidate_session = await _seed_candidate_session(async_session)

    first_run = await eval_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-first",
        day3_final_sha="day3-first",
        cutoff_commit_sha="cutoff-first",
        transcript_reference="transcript:hash:first",
        started_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 3, 11, 12, 5, tzinfo=UTC),
        day_scores=_day_scores(day_index=1, score=82.0, ref="abc111"),
    )
    second_run = await eval_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v5",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-second",
        day3_final_sha="day3-second",
        cutoff_commit_sha="cutoff-second",
        transcript_reference="transcript:hash:second",
        started_at=datetime(2026, 3, 11, 12, 10, tzinfo=UTC),
        completed_at=datetime(2026, 3, 11, 12, 15, tzinfo=UTC),
        day_scores=_day_scores(day_index=2, score=91.0, ref="def222"),
    )

    runs = await eval_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
    )
    assert [run.id for run in runs] == [second_run.id, first_run.id]

    first_fetched = await eval_repo.get_run_by_id(async_session, first_run.id)
    second_fetched = await eval_repo.get_run_by_id(async_session, second_run.id)
    assert first_fetched is not None
    assert second_fetched is not None

    assert first_fetched.day2_checkpoint_sha == "day2-first"
    assert first_fetched.day3_final_sha == "day3-first"
    assert first_fetched.cutoff_commit_sha == "cutoff-first"
    assert first_fetched.transcript_reference == "transcript:hash:first"
    assert first_fetched.day_scores[0].day_index == 1
    assert first_fetched.day_scores[0].evidence_pointers_json[0]["ref"] == "abc111"

    assert second_fetched.day2_checkpoint_sha == "day2-second"
    assert second_fetched.day3_final_sha == "day3-second"
    assert second_fetched.cutoff_commit_sha == "cutoff-second"
    assert second_fetched.transcript_reference == "transcript:hash:second"
    assert second_fetched.day_scores[0].day_index == 2
    assert second_fetched.day_scores[0].evidence_pointers_json[0]["ref"] == "def222"
