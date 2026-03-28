"""Application module for evaluations services evaluations runs service workflows."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.services.evaluations_services_evaluations_runs_coercion_service import (
    coerce_raw_report_json as _coerce_raw_report_json,
)
from app.evaluations.services.evaluations_services_evaluations_runs_coercion_service import (
    coerce_recommendation as _coerce_recommendation,
)
from app.evaluations.services.evaluations_services_evaluations_runs_coercion_service import (
    coerce_unit_interval_score as _coerce_unit_interval_score,
)
from app.evaluations.services.evaluations_services_evaluations_runs_complete_service import (
    complete_run as _complete_run_impl,
)
from app.evaluations.services.evaluations_services_evaluations_runs_fail_service import (
    fail_run as _fail_run_impl,
)
from app.evaluations.services.evaluations_services_evaluations_runs_start_service import (
    start_run as _start_run_impl,
)
from app.evaluations.services.evaluations_services_evaluations_runs_validation_service import (
    EvaluationRunStateError,
)
from app.evaluations.services.evaluations_services_evaluations_runs_validation_service import (
    ensure_transition as _ensure_transition,
)
from app.evaluations.services.evaluations_services_evaluations_runs_validation_service import (
    linked_job_id as _linked_job_id,
)
from app.evaluations.services.evaluations_services_evaluations_runs_validation_service import (
    normalize_datetime as _normalize_datetime,
)
from app.evaluations.services.evaluations_services_evaluations_runs_validation_service import (
    normalize_stored_datetime as _normalize_stored_datetime,
)

eval_repo = evaluation_repo

logger = logging.getLogger(__name__)


async def start_run(db: AsyncSession, **kwargs):
    """Execute start run."""
    return await _start_run_impl(db, logger=logger, **kwargs)


async def complete_run(db: AsyncSession, **kwargs):
    """Complete run."""
    return await _complete_run_impl(db, logger=logger, **kwargs)


async def fail_run(db: AsyncSession, **kwargs):
    """Execute fail run."""
    return await _fail_run_impl(db, logger=logger, **kwargs)


__all__ = [
    "EvaluationRunStateError",
    "_coerce_raw_report_json",
    "_coerce_recommendation",
    "_coerce_unit_interval_score",
    "_ensure_transition",
    "evaluation_repo",
    "eval_repo",
    "_linked_job_id",
    "_normalize_datetime",
    "_normalize_stored_datetime",
    "complete_run",
    "fail_run",
    "start_run",
]
