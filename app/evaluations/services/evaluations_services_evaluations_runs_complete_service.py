"""Application module for evaluations services evaluations runs complete service workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EvaluationRun,
)
from app.evaluations.services.evaluations_services_evaluations_runs_coercion_service import (
    coerce_raw_report_json,
    coerce_recommendation,
    coerce_unit_interval_score,
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


async def complete_run(
    db: AsyncSession,
    *,
    run_id: int,
    day_scores: Sequence[Mapping[str, Any]],
    reviewer_reports: Sequence[Mapping[str, Any]] | None = None,
    overall_winoe_score: float | None = None,
    recommendation: str | None = None,
    confidence: float | None = None,
    raw_report_json: Mapping[str, Any] | None = None,
    completed_at=None,
    generated_at=None,
    metadata_json: Mapping[str, Any] | None = None,
    allow_empty_day_scores: bool = False,
    commit: bool = True,
    logger: Any = None,
) -> EvaluationRun:
    """Complete run."""
    run = await evaluation_repo.get_run_by_id(db, run_id, for_update=True)
    if run is None:
        raise EvaluationRunStateError(f"evaluation run not found: {run_id}")
    ensure_transition(
        current_status=run.status, target_status=EVALUATION_RUN_STATUS_COMPLETED
    )
    await evaluation_repo.add_reviewer_reports(
        db,
        run=run,
        reviewer_reports=reviewer_reports or [],
        allow_empty=True,
        commit=False,
    )
    await evaluation_repo.add_day_scores(
        db,
        run=run,
        day_scores=day_scores,
        allow_empty=allow_empty_day_scores,
        commit=False,
    )
    resolved_completed_at = normalize_datetime(completed_at, field_name="completed_at")
    started_at = normalize_stored_datetime(run.started_at, field_name="started_at")
    if resolved_completed_at < started_at:
        raise EvaluationRunStateError(
            "completed_at must be greater than or equal to started_at."
        )
    resolved_generated_at = normalize_datetime(generated_at, field_name="generated_at")
    if resolved_generated_at < started_at:
        raise EvaluationRunStateError(
            "generated_at must be greater than or equal to started_at."
        )
    run.status = EVALUATION_RUN_STATUS_COMPLETED
    run.completed_at = resolved_completed_at
    run.generated_at = resolved_generated_at
    run.overall_winoe_score = coerce_unit_interval_score(
        overall_winoe_score, field_name="overall_winoe_score", required=False
    )
    run.recommendation = coerce_recommendation(recommendation, required=False)
    run.confidence = coerce_unit_interval_score(
        confidence, field_name="confidence", required=False
    )
    run.raw_report_json = coerce_raw_report_json(raw_report_json)
    run.error_code = None
    if metadata_json is not None:
        if not isinstance(metadata_json, Mapping):
            raise EvaluationRunStateError(
                "metadata_json must be an object when provided."
            )
        run.metadata_json = dict(metadata_json)
    if commit:
        await db.commit()
    else:
        await db.flush()
    if logger is not None:
        logger.info(
            "Evaluation run completed runId=%s candidateSessionId=%s scenarioVersionId=%s durationMs=%s linkedJobId=%s modelName=%s modelVersion=%s promptVersion=%s rubricVersion=%s basisFingerprint=%s",
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
        )
    return run


__all__ = ["complete_run"]
