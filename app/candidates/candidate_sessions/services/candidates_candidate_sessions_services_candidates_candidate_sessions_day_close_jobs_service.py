"""Application module for candidates candidate sessions services candidates candidate sessions day close jobs service workflows."""

from __future__ import annotations

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_constants import (
    DAY_CLOSE_ENFORCEMENT_DAY_INDEXES,
    DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
    DAY_CLOSE_ENFORCEMENT_MAX_ATTEMPTS,
    DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES,
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
    DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS,
    day_close_enforcement_idempotency_key,
    day_close_finalize_text_idempotency_key,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_enqueue_service import (
    enqueue_day_close_enforcement_jobs_impl,
    enqueue_day_close_finalize_text_jobs_impl,
    enqueue_day_close_jobs_impl,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_payloads_service import (
    build_day_close_enforcement_payload,
    build_day_close_finalize_text_payload,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_queries_service import (
    _load_tasks_for_day_indexes,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_specs_service import (
    _enforcement_job_spec,
    _finalize_text_job_spec,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_upsert_service import (
    _upsert_day_close_jobs,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_gates_service import (
    compute_task_window,
)


async def enqueue_day_close_finalize_text_jobs(
    db, *, candidate_session, commit: bool = False
):
    """Enqueue day close finalize text jobs."""
    return await enqueue_day_close_finalize_text_jobs_impl(
        db=db,
        candidate_session=candidate_session,
        load_tasks_for_day_indexes=_load_tasks_for_day_indexes,
        compute_task_window=compute_task_window,
        upsert_day_close_jobs=_upsert_day_close_jobs,
        finalize_text_job_spec=_finalize_text_job_spec,
        commit=commit,
    )


async def enqueue_day_close_enforcement_jobs(
    db, *, candidate_session, commit: bool = False
):
    """Enqueue day close enforcement jobs."""
    return await enqueue_day_close_enforcement_jobs_impl(
        db=db,
        candidate_session=candidate_session,
        load_tasks_for_day_indexes=_load_tasks_for_day_indexes,
        compute_task_window=compute_task_window,
        upsert_day_close_jobs=_upsert_day_close_jobs,
        enforcement_job_spec=_enforcement_job_spec,
        commit=commit,
    )


async def enqueue_day_close_jobs(db, *, candidate_session, commit: bool = False):
    """Enqueue day close jobs."""
    return await enqueue_day_close_jobs_impl(
        db=db,
        candidate_session=candidate_session,
        load_tasks_for_day_indexes=_load_tasks_for_day_indexes,
        compute_task_window=compute_task_window,
        upsert_day_close_jobs=_upsert_day_close_jobs,
        finalize_text_job_spec=_finalize_text_job_spec,
        enforcement_job_spec=_enforcement_job_spec,
        commit=commit,
    )


__all__ = [
    "DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE",
    "DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS",
    "DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES",
    "DAY_CLOSE_ENFORCEMENT_JOB_TYPE",
    "DAY_CLOSE_ENFORCEMENT_MAX_ATTEMPTS",
    "DAY_CLOSE_ENFORCEMENT_DAY_INDEXES",
    "build_day_close_finalize_text_payload",
    "build_day_close_enforcement_payload",
    "day_close_finalize_text_idempotency_key",
    "day_close_enforcement_idempotency_key",
    "enqueue_day_close_jobs",
    "enqueue_day_close_finalize_text_jobs",
    "enqueue_day_close_enforcement_jobs",
]
