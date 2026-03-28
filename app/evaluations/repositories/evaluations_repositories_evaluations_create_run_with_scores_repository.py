"""Application module for evaluations repositories evaluations create run with scores repository workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_PENDING,
    EvaluationRun,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_create_run_repository import (
    create_run,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_day_scores_repository import (
    add_day_scores,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_queries_repository import (
    get_run_by_id,
)


async def create_run_with_day_scores(
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
    day_scores: Sequence[Mapping[str, Any]],
    job_id: str | None = None,
    basis_fingerprint: str | None = None,
    overall_fit_score: float | None = None,
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
    """Create run with day scores."""
    run = await create_run(
        db,
        candidate_session_id=candidate_session_id,
        scenario_version_id=scenario_version_id,
        model_name=model_name,
        model_version=model_version,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
        day2_checkpoint_sha=day2_checkpoint_sha,
        day3_final_sha=day3_final_sha,
        cutoff_commit_sha=cutoff_commit_sha,
        transcript_reference=transcript_reference,
        job_id=job_id,
        basis_fingerprint=basis_fingerprint,
        overall_fit_score=overall_fit_score,
        recommendation=recommendation,
        confidence=confidence,
        generated_at=generated_at,
        raw_report_json=raw_report_json,
        error_code=error_code,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        metadata_json=metadata_json,
        commit=False,
    )
    await add_day_scores(
        db, run=run, day_scores=day_scores, allow_empty=False, commit=False
    )
    if commit:
        await db.commit()
        return await get_run_by_id(db, run.id) or run
    await db.flush()
    return run
