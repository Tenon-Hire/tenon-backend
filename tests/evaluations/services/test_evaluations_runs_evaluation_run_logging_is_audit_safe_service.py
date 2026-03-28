from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


@pytest.mark.asyncio
async def test_evaluation_run_logging_is_audit_safe(async_session, caplog):
    candidate_session = await _seed_candidate_session(async_session)
    sensitive_transcript_ref = "transcript:hash:sensitive-ref"
    sensitive_excerpt = "candidate said highly sensitive thing"
    day_scores = [
        {
            "day_index": 3,
            "score": 91,
            "rubric_results_json": {"quality": 5},
            "evidence_pointers_json": [
                {
                    "kind": "transcript",
                    "startMs": 200,
                    "endMs": 2400,
                    "excerpt": sensitive_excerpt,
                }
            ],
        }
    ]

    caplog.set_level(
        "INFO",
        logger="app.evaluations.services.evaluations_services_evaluations_runs_service",
    )

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
        transcript_reference=sensitive_transcript_ref,
        metadata_json={"jobId": "job_123"},
    )
    await eval_service.complete_run(
        async_session,
        run_id=started.id,
        day_scores=day_scores,
        metadata_json={"jobId": "job_123"},
    )

    started_for_fail = await eval_service.start_run(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha-2",
        day3_final_sha="day3-sha-2",
        cutoff_commit_sha="cutoff-sha-2",
        transcript_reference=sensitive_transcript_ref,
        metadata_json={"job_id": "job_456"},
    )
    await eval_service.fail_run(
        async_session,
        run_id=started_for_fail.id,
        metadata_json={"job_id": "job_456"},
        error_message="timeout",
    )

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "Evaluation run started" in log_text
    assert "Evaluation run completed" in log_text
    assert "Evaluation run failed" in log_text
    assert f"runId={started.id}" in log_text
    assert "durationMs=" in log_text
    assert "linkedJobId=" in log_text
    assert sensitive_transcript_ref not in log_text
    assert sensitive_excerpt not in log_text
