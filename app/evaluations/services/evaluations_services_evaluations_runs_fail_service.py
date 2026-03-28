"""Application module for evaluations services evaluations runs fail service workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_FAILED,
    EvaluationRun,
)
from app.evaluations.services.evaluations_services_evaluations_runs_validation_service import (
    EvaluationRunStateError,
    ensure_transition,
    linked_job_id,
    normalize_datetime,
    normalize_stored_datetime,
)


def _duration_ms(*, started_at, completed_at) -> int:
    normalized_started_at = normalize_stored_datetime(
        started_at, field_name="started_at"
    )
    normalized_completed_at = normalize_stored_datetime(
        completed_at, field_name="completed_at"
    )
    return int((normalized_completed_at - normalized_started_at).total_seconds() * 1000)


async def fail_run(
    db: AsyncSession,
    *,
    run_id: int,
    completed_at=None,
    error_code: str | None = None,
    metadata_json: Mapping[str, Any] | None = None,
    error_message: str | None = None,
    commit: bool = True,
    logger: Any = None,
) -> EvaluationRun:
    """Execute fail run."""
    run = await evaluation_repo.get_run_by_id(db, run_id, for_update=True)
    if run is None:
        raise EvaluationRunStateError(f"evaluation run not found: {run_id}")
    ensure_transition(
        current_status=run.status, target_status=EVALUATION_RUN_STATUS_FAILED
    )
    resolved_completed_at = normalize_datetime(completed_at, field_name="completed_at")
    started_at = normalize_stored_datetime(run.started_at, field_name="started_at")
    if resolved_completed_at < started_at:
        raise EvaluationRunStateError(
            "completed_at must be greater than or equal to started_at."
        )
    merged_metadata: dict[str, Any] = {}
    if isinstance(run.metadata_json, Mapping):
        merged_metadata.update(run.metadata_json)
    if metadata_json is not None:
        if not isinstance(metadata_json, Mapping):
            raise EvaluationRunStateError(
                "metadata_json must be an object when provided."
            )
        merged_metadata.update(metadata_json)
    if error_message:
        merged_metadata["error"] = error_message
    run.status = EVALUATION_RUN_STATUS_FAILED
    run.completed_at = resolved_completed_at
    run.error_code = (error_code or "").strip() or None
    run.metadata_json = merged_metadata or None
    if commit:
        await db.commit()
    else:
        await db.flush()
    if logger is not None:
        logger.warning(
            "Evaluation run failed runId=%s candidateSessionId=%s scenarioVersionId=%s durationMs=%s linkedJobId=%s modelName=%s modelVersion=%s promptVersion=%s rubricVersion=%s basisFingerprint=%s errorCode=%s",
            run.id,
            run.candidate_session_id,
            run.scenario_version_id,
            _duration_ms(started_at=run.started_at, completed_at=run.completed_at),
            linked_job_id(run.metadata_json),
            run.model_name,
            run.model_version,
            run.prompt_version,
            run.rubric_version,
            run.basis_fingerprint,
            run.error_code,
        )
    return run


__all__ = ["fail_run"]
