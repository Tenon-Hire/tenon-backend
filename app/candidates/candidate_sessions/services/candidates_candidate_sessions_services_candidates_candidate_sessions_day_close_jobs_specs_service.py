"""Application module for candidates candidate sessions services candidates candidate sessions day close jobs specs service workflows."""

from __future__ import annotations

from datetime import datetime

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_constants import (
    DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
    DAY_CLOSE_ENFORCEMENT_MAX_ATTEMPTS,
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
    DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS,
    day_close_enforcement_idempotency_key,
    day_close_finalize_text_idempotency_key,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_payloads_service import (
    build_day_close_enforcement_payload,
    build_day_close_finalize_text_payload,
)
from app.shared.jobs.repositories import repository as jobs_repo


def _finalize_text_job_spec(
    *, candidate_session_id: int, task_id: int, day_index: int, window_end_at: datetime
) -> jobs_repo.IdempotentJobSpec:
    return jobs_repo.IdempotentJobSpec(
        job_type=DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
        idempotency_key=day_close_finalize_text_idempotency_key(
            candidate_session_id, task_id
        ),
        payload_json=build_day_close_finalize_text_payload(
            candidate_session_id=candidate_session_id,
            task_id=task_id,
            day_index=day_index,
            window_end_at=window_end_at,
        ),
        candidate_session_id=candidate_session_id,
        max_attempts=DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS,
        correlation_id=f"candidate_session:{candidate_session_id}:schedule",
        next_run_at=window_end_at,
    )


def _enforcement_job_spec(
    *, candidate_session_id: int, task_id: int, day_index: int, window_end_at: datetime
) -> jobs_repo.IdempotentJobSpec:
    return jobs_repo.IdempotentJobSpec(
        job_type=DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        idempotency_key=day_close_enforcement_idempotency_key(
            candidate_session_id, day_index
        ),
        payload_json=build_day_close_enforcement_payload(
            candidate_session_id=candidate_session_id,
            task_id=task_id,
            day_index=day_index,
            window_end_at=window_end_at,
        ),
        candidate_session_id=candidate_session_id,
        max_attempts=DAY_CLOSE_ENFORCEMENT_MAX_ATTEMPTS,
        correlation_id=f"candidate_session:{candidate_session_id}:schedule",
        next_run_at=window_end_at,
    )


__all__ = ["_enforcement_job_spec", "_finalize_text_job_spec"]
