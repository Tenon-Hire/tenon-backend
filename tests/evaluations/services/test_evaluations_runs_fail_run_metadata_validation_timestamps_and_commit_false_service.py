from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


@pytest.mark.asyncio
async def test_fail_run_metadata_validation_timestamps_and_commit_false(async_session):
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

    with pytest.raises(
        eval_service.EvaluationRunStateError,
        match="greater than or equal",
    ):
        await eval_service.fail_run(
            async_session,
            run_id=started.id,
            completed_at=datetime(2026, 3, 11, 11, 59, tzinfo=UTC),
        )

    with pytest.raises(
        eval_service.EvaluationRunStateError, match="metadata_json must be an object"
    ):
        await eval_service.fail_run(
            async_session,
            run_id=started.id,
            metadata_json=["invalid"],  # type: ignore[arg-type]
        )

    failed = await eval_service.fail_run(
        async_session,
        run_id=started.id,
        metadata_json={"job_id": "job_002"},
        error_message="model timeout",
        commit=False,
    )
    assert failed.status == EVALUATION_RUN_STATUS_FAILED
    assert failed.completed_at is not None
    assert failed.metadata_json is not None
    assert failed.metadata_json["jobId"] == "job_001"
    assert failed.metadata_json["job_id"] == "job_002"
    assert failed.metadata_json["error"] == "model timeout"
    assert failed.day2_checkpoint_sha == "day2-sha"
    assert failed.day3_final_sha == "day3-sha"
    assert failed.cutoff_commit_sha == "cutoff-sha"
    assert failed.transcript_reference == "transcript:hash:abcd"
