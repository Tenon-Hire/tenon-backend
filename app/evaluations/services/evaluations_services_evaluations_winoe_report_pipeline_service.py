"""Application module for evaluations services evaluations winoe report pipeline service workflows."""

from __future__ import annotations

import logging
from typing import Any

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.services import (
    evaluations_services_evaluations_evaluator_service as evaluator_service,
)
from app.evaluations.services import (
    evaluations_services_evaluations_runs_service as evaluation_runs,
)
from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_pipeline_transcript_service as transcript_ops,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_access_service import (
    get_candidate_session_evaluation_context,
    has_company_access,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_basis_service import (
    _build_basis_references,
    _stable_hash,
    _submission_basis_hash,
    _transcript_basis_hash,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_constants_service import (
    DEFAULT_EVALUATION_MODEL_NAME,
    DEFAULT_EVALUATION_MODEL_VERSION,
    DEFAULT_EVALUATION_PROMPT_VERSION,
    DEFAULT_RUBRIC_VERSION,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_parse_service import (
    _normalize_day_toggles,
    _normalize_transcript_segments,
    _parse_diff_summary,
    _parse_positive_int,
    _safe_int,
    _segment_end_ms,
    _segment_start_ms,
    _segment_text,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_queries_service import (
    _day_audits_by_day,
    _submissions_by_day,
    _tasks_by_day,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_runner_service import (
    process_evaluation_run_job_impl,
)
from app.shared.database import async_session_maker
from app.submissions.repositories import (
    submissions_repositories_submissions_winoe_report_repository as winoe_report_repository,
)

logger = logging.getLogger(__name__)
recordings_repo = transcript_ops.recordings_repo


async def _resolve_day4_transcript(*args: Any, **kwargs: Any):
    transcript_ops.recordings_repo = recordings_repo
    return await transcript_ops._resolve_day4_transcript(*args, **kwargs)


async def process_evaluation_run_job(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Process evaluation run job."""
    return await process_evaluation_run_job_impl(
        payload_json,
        async_session_maker=async_session_maker,
        get_candidate_session_evaluation_context=get_candidate_session_evaluation_context,
        has_company_access=has_company_access,
        _tasks_by_day=_tasks_by_day,
        _submissions_by_day=_submissions_by_day,
        _day_audits_by_day=_day_audits_by_day,
        _resolve_day4_transcript=_resolve_day4_transcript,
        evaluation_repo=evaluation_repo,
        evaluation_runs=evaluation_runs,
        winoe_report_repository=winoe_report_repository,
        evaluator_service=evaluator_service,
        logger=logger,
    )


__all__ = [
    "DEFAULT_EVALUATION_MODEL_NAME",
    "DEFAULT_EVALUATION_MODEL_VERSION",
    "DEFAULT_EVALUATION_PROMPT_VERSION",
    "DEFAULT_RUBRIC_VERSION",
    "_build_basis_references",
    "_normalize_day_toggles",
    "_normalize_transcript_segments",
    "_parse_diff_summary",
    "_parse_positive_int",
    "_safe_int",
    "_segment_end_ms",
    "_segment_start_ms",
    "_segment_text",
    "_stable_hash",
    "_submission_basis_hash",
    "_transcript_basis_hash",
    "process_evaluation_run_job",
]
