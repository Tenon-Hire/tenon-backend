"""Application module for evaluations services evaluations runs start service workflows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_RUNNING,
    EvaluationRun,
)
from app.evaluations.services.evaluations_services_evaluations_runs_validation_service import (
    linked_job_id,
)


async def start_run(
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
    metadata_json: Mapping[str, Any] | None = None,
    started_at: datetime | None = None,
    commit: bool = True,
    logger: Any = None,
) -> EvaluationRun:
    """Execute start run."""
    run = await evaluation_repo.create_run(
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
        status=EVALUATION_RUN_STATUS_RUNNING,
        started_at=started_at,
        metadata_json=metadata_json,
        commit=commit,
    )
    if logger is not None:
        logger.info(
            "Evaluation run started runId=%s candidateSessionId=%s scenarioVersionId=%s modelName=%s modelVersion=%s promptVersion=%s rubricVersion=%s basisFingerprint=%s linkedJobId=%s",
            run.id,
            run.candidate_session_id,
            run.scenario_version_id,
            run.model_name,
            run.model_version,
            run.prompt_version,
            run.rubric_version,
            run.basis_fingerprint,
            linked_job_id(run.metadata_json),
        )
    return run


__all__ = ["start_run"]
