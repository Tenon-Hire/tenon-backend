"""Application module for jobs handlers day close finalize text window handler workflows."""

from __future__ import annotations

from datetime import datetime

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_service import (
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
    build_day_close_finalize_text_payload,
    day_close_finalize_text_idempotency_key,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.submissions.services.submissions_services_submissions_payload_validation_service import (
    TEXT_TASK_TYPES,
)


def _non_text_task_response(*, candidate_session_id: int, task_id: int, task) -> dict:
    task_type = (task.type or "").strip().lower()
    if task_type in TEXT_TASK_TYPES:
        return {}
    return {
        "status": "skipped_non_text_task",
        "candidateSessionId": candidate_session_id,
        "taskId": task_id,
        "dayIndex": task.day_index,
        "taskType": task_type,
    }


async def _window_gate_or_reschedule(
    db,
    *,
    candidate_session,
    task,
    candidate_session_id: int,
    task_id: int,
    now,
    scheduled_window_end_at: datetime | None,
    compute_task_window,
    logger,
) -> dict | None:
    task_window = compute_task_window(candidate_session, task, now_utc=now)
    window_end_at = task_window.window_end_at
    if window_end_at is None:
        return {
            "status": "skipped_invalid_window",
            "candidateSessionId": candidate_session_id,
            "taskId": task_id,
            "dayIndex": task.day_index,
        }
    if now < window_end_at:
        trial = candidate_session.trial
        company_id = getattr(trial, "company_id", None)
        if company_id is None:
            raise RuntimeError("company_id required to reschedule")
        payload = build_day_close_finalize_text_payload(
            candidate_session_id=candidate_session_id,
            task_id=task_id,
            day_index=task.day_index,
            window_end_at=window_end_at,
        )
        rescheduled = await jobs_repo.requeue_nonterminal_idempotent_job(
            db,
            company_id=company_id,
            job_type=DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
            idempotency_key=day_close_finalize_text_idempotency_key(
                candidate_session_id, task_id
            ),
            next_run_at=window_end_at,
            now=now,
            payload_json=payload,
            commit=True,
        )
        if rescheduled is None:
            raise RuntimeError("unable to reschedule idempotent job")
        logger.info(
            "Day-close finalize rescheduled-not-due candidateSessionId=%s taskId=%s dayIndex=%s windowEndAt=%s",
            candidate_session_id,
            task_id,
            task.day_index,
            window_end_at.isoformat(),
        )
        return {
            "status": "rescheduled_not_due",
            "_jobDisposition": "rescheduled",
            "candidateSessionId": candidate_session_id,
            "taskId": task_id,
            "dayIndex": task.day_index,
            "windowEndAt": window_end_at.isoformat(),
            "scheduledWindowEndAt": scheduled_window_end_at.isoformat()
            if scheduled_window_end_at is not None
            else None,
        }
    return None


__all__ = ["_non_text_task_response", "_window_gate_or_reschedule"]
