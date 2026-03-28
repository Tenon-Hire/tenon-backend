from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


@pytest.mark.asyncio
async def test_start_and_complete_run_with_immutable_basis(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    started_at = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)

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
        metadata_json={"jobId": "job_001"},
        started_at=started_at,
    )

    completed = await eval_service.complete_run(
        async_session,
        run_id=started.id,
        day_scores=_day_scores_payload(),
        completed_at=datetime(2026, 3, 11, 12, 8, tzinfo=UTC),
    )
    assert completed.status == "completed"
    assert completed.completed_at == datetime(2026, 3, 11, 12, 8, tzinfo=UTC)
    assert completed.day2_checkpoint_sha == "day2-sha"
    assert completed.day3_final_sha == "day3-sha"
    assert completed.cutoff_commit_sha == "cutoff-sha"
    assert completed.transcript_reference == "transcript:hash:abcd"

    fetched = await eval_repo.get_run_by_id(async_session, completed.id)
    assert fetched is not None
    assert fetched.day2_checkpoint_sha == "day2-sha"
    assert fetched.day3_final_sha == "day3-sha"
    assert fetched.cutoff_commit_sha == "cutoff-sha"
    assert fetched.transcript_reference == "transcript:hash:abcd"
    assert len(fetched.day_scores) == 2
