"""Application module for evaluations services evaluations fit profile pipeline run state service workflows."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
)
from app.evaluations.services.evaluations_services_evaluations_fit_profile_pipeline_constants_service import (
    DEFAULT_EVALUATION_MODEL_NAME,
    DEFAULT_EVALUATION_MODEL_VERSION,
    DEFAULT_EVALUATION_PROMPT_VERSION,
)


def _completed_response(
    *, run, candidate_session_id: int, duration_ms: int
) -> dict[str, Any]:
    return {
        "status": "completed",
        "candidateSessionId": candidate_session_id,
        "evaluationRunId": run.id,
        "basisFingerprint": run.basis_fingerprint,
        "durationMs": duration_ms,
        "modelVersion": run.model_version,
        "promptVersion": run.prompt_version,
        "rubricVersion": run.rubric_version,
    }


def _failed_response(
    *, run, candidate_session_id: int, duration_ms: int
) -> dict[str, Any]:
    return {
        "status": "failed",
        "candidateSessionId": candidate_session_id,
        "evaluationRunId": run.id,
        "errorCode": run.error_code or "evaluation_failed",
        "durationMs": duration_ms,
    }


async def _get_or_start_run(
    *,
    db,
    context,
    evaluation_repo,
    evaluation_runs,
    job_id: str | None,
    started: float,
    run_metadata: dict[str, Any],
    basis_fingerprint: str,
    scenario_rubric_version: str,
    day2_checkpoint_sha: str,
    day3_final_sha: str,
    cutoff_commit_sha: str,
    transcript_reference: str,
) -> tuple[Any, dict[str, Any] | None]:
    existing_run = None
    if job_id is not None:
        existing_run = await evaluation_repo.get_run_by_job_id(
            db,
            job_id=job_id,
            candidate_session_id=context.candidate_session.id,
            for_update=True,
        )
    if existing_run is None:
        run = await evaluation_runs.start_run(
            db,
            candidate_session_id=context.candidate_session.id,
            scenario_version_id=context.candidate_session.scenario_version_id,
            model_name=DEFAULT_EVALUATION_MODEL_NAME,
            model_version=DEFAULT_EVALUATION_MODEL_VERSION,
            prompt_version=DEFAULT_EVALUATION_PROMPT_VERSION,
            rubric_version=scenario_rubric_version,
            day2_checkpoint_sha=day2_checkpoint_sha,
            day3_final_sha=day3_final_sha,
            cutoff_commit_sha=cutoff_commit_sha,
            transcript_reference=transcript_reference,
            job_id=job_id,
            basis_fingerprint=basis_fingerprint,
            metadata_json=run_metadata,
            commit=False,
        )
        return run, None

    run = existing_run
    duration_ms = int((perf_counter() - started) * 1000)
    if run.status == EVALUATION_RUN_STATUS_COMPLETED:
        return run, _completed_response(
            run=run,
            candidate_session_id=context.candidate_session.id,
            duration_ms=duration_ms,
        )
    if run.status == EVALUATION_RUN_STATUS_FAILED:
        return run, _failed_response(
            run=run,
            candidate_session_id=context.candidate_session.id,
            duration_ms=duration_ms,
        )
    return run, None


__all__ = ["_completed_response", "_failed_response", "_get_or_start_run"]
