"""Application module for evaluations repositories evaluations create run repository workflows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_PENDING,
    EvaluationRun,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_create_run_helpers_repository import (
    normalize_run_time_fields,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_validation_scalars_repository import (
    coerce_object,
    coerce_recommendation,
    coerce_unit_interval_score,
    normalize_non_empty_str,
    normalize_optional_non_empty_str,
    normalize_status,
)


async def create_run(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    scenario_version_id: int,
    model_name: str,
    model_version: str,
    prompt_version: str,
    rubric_version: str,
    day2_checkpoint_sha: str,
    day3_final_sha: str,
    cutoff_commit_sha: str,
    transcript_reference: str,
    job_id: str | None = None,
    basis_fingerprint: str | None = None,
    overall_winoe_score: float | None = None,
    recommendation: str | None = None,
    confidence: float | None = None,
    generated_at: datetime | None = None,
    raw_report_json: Mapping[str, Any] | None = None,
    error_code: str | None = None,
    status: str = EVALUATION_RUN_STATUS_PENDING,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    metadata_json: Mapping[str, Any] | None = None,
    commit: bool = True,
) -> EvaluationRun:
    """Create run."""
    normalized_status = normalize_status(status)
    (
        normalized_started_at,
        normalized_completed_at,
        normalized_generated_at,
    ) = normalize_run_time_fields(
        status=normalized_status,
        started_at=started_at,
        completed_at=completed_at,
        generated_at=generated_at,
    )
    run = EvaluationRun(
        candidate_session_id=int(candidate_session_id),
        scenario_version_id=int(scenario_version_id),
        status=normalized_status,
        started_at=normalized_started_at,
        completed_at=normalized_completed_at,
        model_name=normalize_non_empty_str(model_name, field_name="model_name"),
        model_version=normalize_non_empty_str(
            model_version, field_name="model_version"
        ),
        prompt_version=normalize_non_empty_str(
            prompt_version, field_name="prompt_version"
        ),
        rubric_version=normalize_non_empty_str(
            rubric_version, field_name="rubric_version"
        ),
        job_id=normalize_optional_non_empty_str(job_id, field_name="job_id"),
        basis_fingerprint=normalize_optional_non_empty_str(
            basis_fingerprint, field_name="basis_fingerprint"
        ),
        overall_winoe_score=coerce_unit_interval_score(
            overall_winoe_score, field_name="overall_winoe_score"
        ),
        recommendation=coerce_recommendation(recommendation),
        confidence=coerce_unit_interval_score(confidence, field_name="confidence"),
        generated_at=normalized_generated_at,
        raw_report_json=coerce_object(raw_report_json, field_name="raw_report_json"),
        error_code=normalize_optional_non_empty_str(
            error_code, field_name="error_code"
        ),
        metadata_json=coerce_object(metadata_json, field_name="metadata_json"),
        day2_checkpoint_sha=normalize_non_empty_str(
            day2_checkpoint_sha, field_name="day2_checkpoint_sha"
        ),
        day3_final_sha=normalize_non_empty_str(
            day3_final_sha, field_name="day3_final_sha"
        ),
        cutoff_commit_sha=normalize_non_empty_str(
            cutoff_commit_sha, field_name="cutoff_commit_sha"
        ),
        transcript_reference=normalize_non_empty_str(
            transcript_reference, field_name="transcript_reference"
        ),
    )
    db.add(run)
    if commit:
        await db.commit()
        await db.refresh(run)
    else:
        await db.flush()
    return run
