from __future__ import annotations

import pytest

from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_evidence_pointer_validation_additional_errors(async_session):
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

    cases = [
        (
            [123],
            "must be an object",
        ),
        (
            [{"url": "https://github.com/acme/repo/commit/abc123"}],
            "kind must be a non-empty string",
        ),
        (
            [{"kind": "commit", "ref": "abc123", "excerpt": 123}],
            "excerpt must be a string",
        ),
        (
            [{"kind": "transcript", "startMs": -1, "endMs": 10}],
            "must be non-negative",
        ),
        (
            [{"kind": "transcript", "startMs": 20, "endMs": 10}],
            "greater than or equal to startMs",
        ),
        (
            [{"kind": "commit", "ref": "abc123", "url": "   "}],
            "non-empty string",
        ),
        (
            [{"kind": "commit", "ref": "   "}],
            "ref must be a non-empty string",
        ),
    ]

    for pointers, match in cases:
        with pytest.raises(eval_repo.EvidencePointerValidationError, match=match):
            await eval_repo.create_run_with_day_scores(
                async_session,
                **base_kwargs,
                day_scores=[
                    {
                        "day_index": 2,
                        "score": 90,
                        "rubric_results_json": {"delivery": 5},
                        "evidence_pointers_json": pointers,
                    }
                ],
            )
        await async_session.rollback()
