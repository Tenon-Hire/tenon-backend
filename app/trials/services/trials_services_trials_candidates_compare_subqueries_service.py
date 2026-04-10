"""Application module for trials services trials candidates compare subqueries service workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_jobs_service import (
    EVALUATION_RUN_JOB_TYPE,
)
from app.shared.database.shared_database_models_model import EvaluationRun, Job
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)


def latest_run_subquery(*, completed_only: bool) -> Any:
    """Execute latest run subquery."""
    base_stmt = select(
        EvaluationRun.candidate_session_id.label("candidate_session_id"),
        EvaluationRun.status.label("run_status"),
        EvaluationRun.started_at.label("run_started_at"),
        EvaluationRun.completed_at.label("run_completed_at"),
        EvaluationRun.generated_at.label("run_generated_at"),
        EvaluationRun.overall_winoe_score.label("overall_winoe_score"),
        EvaluationRun.recommendation.label("recommendation"),
        func.row_number()
        .over(
            partition_by=EvaluationRun.candidate_session_id,
            order_by=(EvaluationRun.started_at.desc(), EvaluationRun.id.desc()),
        )
        .label("rn"),
    )
    if completed_only:
        base_stmt = base_stmt.where(
            EvaluationRun.status == EVALUATION_RUN_STATUS_COMPLETED
        )
    ranked = base_stmt.subquery()
    return (
        select(
            ranked.c.candidate_session_id,
            ranked.c.run_status,
            ranked.c.run_started_at,
            ranked.c.run_completed_at,
            ranked.c.run_generated_at,
            ranked.c.overall_winoe_score,
            ranked.c.recommendation,
        )
        .where(ranked.c.rn == 1)
        .subquery()
    )


def active_job_subquery() -> Any:
    """Execute active job subquery."""
    return (
        select(
            Job.candidate_session_id.label("candidate_session_id"),
            func.max(Job.updated_at).label("active_job_updated_at"),
        )
        .where(
            Job.candidate_session_id.is_not(None),
            Job.job_type == EVALUATION_RUN_JOB_TYPE,
            Job.status.in_((JOB_STATUS_QUEUED, JOB_STATUS_RUNNING)),
        )
        .group_by(Job.candidate_session_id)
        .subquery()
    )


__all__ = ["active_job_subquery", "latest_run_subquery"]
