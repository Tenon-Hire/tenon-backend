from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_create_run_validation_guards(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    base_kwargs = {
        "candidate_session_id": candidate_session.id,
        "scenario_version_id": candidate_session.scenario_version_id,
        "model_name": "gpt-5-evaluator",
        "model_version": "2026-03-11",
        "prompt_version": "prompt.v4",
        "rubric_version": "rubric.v2",
        "day2_checkpoint_sha": "day2-sha",
        "day3_final_sha": "day3-sha",
        "cutoff_commit_sha": "cutoff-sha",
        "transcript_reference": "transcript:hash:abcd",
    }

    with pytest.raises(ValueError, match="invalid evaluation run status"):
        await eval_repo.create_run(
            async_session,
            **base_kwargs,
            status="unknown-status",
        )
    with pytest.raises(ValueError, match="metadata_json must be an object"):
        await eval_repo.create_run(
            async_session,
            **base_kwargs,
            metadata_json=["bad"],  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="started_at must be a datetime"):
        await eval_repo.create_run(
            async_session,
            **base_kwargs,
            started_at="bad",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="model_name must be a non-empty string"):
        await eval_repo.create_run(
            async_session,
            **{**base_kwargs, "model_name": "   "},
        )
    with pytest.raises(ValueError, match="completed_at is not allowed"):
        await eval_repo.create_run(
            async_session,
            **base_kwargs,
            status=EVALUATION_RUN_STATUS_PENDING,
            completed_at=datetime(2026, 3, 11, 12, 3, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="completed_at is not allowed"):
        await eval_repo.create_run(
            async_session,
            **base_kwargs,
            status=EVALUATION_RUN_STATUS_RUNNING,
            completed_at=datetime(2026, 3, 11, 12, 3, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="greater than or equal"):
        await eval_repo.create_run(
            async_session,
            **base_kwargs,
            status=EVALUATION_RUN_STATUS_COMPLETED,
            started_at=datetime(2026, 3, 11, 12, 5, tzinfo=UTC),
            completed_at=datetime(2026, 3, 11, 12, 4, tzinfo=UTC),
        )

    naive_started_at = datetime(2026, 3, 11, 12, 0)
    completed = await eval_repo.create_run(
        async_session,
        **base_kwargs,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        started_at=naive_started_at,
        completed_at=None,
        commit=False,
    )
    assert completed.started_at.tzinfo is not None
    assert completed.completed_at is not None
