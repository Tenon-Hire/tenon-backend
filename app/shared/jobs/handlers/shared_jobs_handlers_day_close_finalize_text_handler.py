"""Application module for jobs handlers day close finalize text handler workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.candidates.candidate_sessions import services as cs_service
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_service import (
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
)
from app.shared.database import async_session_maker
from app.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_parsing_handler import (
    _parse_optional_datetime,
    _parse_positive_int,
)
from app.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_queries_handler import (
    _get_existing_submission as _get_existing_submission_impl,
)
from app.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_queries_handler import (
    _load_candidate_session,
    _load_task_for_session,
)
from app.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_submission_handler import (
    _finalize_submission_from_cutoff,
)
from app.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_window_handler import (
    _non_text_task_response,
    _window_gate_or_reschedule,
)
from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    SubmissionConflict,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)

logger = logging.getLogger(__name__)


async def _get_existing_submission(db, *, candidate_session_id: int, task_id: int):
    return await _get_existing_submission_impl(
        db, candidate_session_id=candidate_session_id, task_id=task_id
    )


async def handle_day_close_finalize_text(
    payload_json: dict[str, Any],
) -> dict[str, Any]:
    """Handle day close finalize text."""
    candidate_session_id = _parse_positive_int(payload_json.get("candidateSessionId"))
    task_id = _parse_positive_int(payload_json.get("taskId"))
    day_index = _parse_positive_int(payload_json.get("dayIndex"))
    scheduled_window_end_at = _parse_optional_datetime(payload_json.get("windowEndAt"))
    if candidate_session_id is None or task_id is None:
        return {
            "status": "skipped_invalid_payload",
            "candidateSessionId": candidate_session_id,
            "taskId": task_id,
            "dayIndex": day_index,
        }
    now = datetime.now(UTC)
    async with async_session_maker() as db:
        candidate_session = await _load_candidate_session(
            db, candidate_session_id=candidate_session_id
        )
        if candidate_session is None:
            return {
                "status": "candidate_session_not_found",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": day_index,
            }
        task = await _load_task_for_session(
            db, task_id=task_id, trial_id=candidate_session.trial_id
        )
        if task is None:
            return {
                "status": "task_not_found",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": day_index,
            }
        non_text = _non_text_task_response(
            candidate_session_id=candidate_session_id, task_id=task_id, task=task
        )
        if non_text:
            return non_text
        window_result = await _window_gate_or_reschedule(
            db,
            candidate_session=candidate_session,
            task=task,
            candidate_session_id=candidate_session_id,
            task_id=task_id,
            now=now,
            scheduled_window_end_at=scheduled_window_end_at,
            compute_task_window=cs_service.compute_task_window,
            logger=logger,
        )
        if window_result is not None:
            return window_result
        return await _finalize_submission_from_cutoff(
            db,
            candidate_session=candidate_session,
            task=task,
            candidate_session_id=candidate_session_id,
            task_id=task_id,
            now=now,
            get_existing_submission=_get_existing_submission,
            create_submission=submission_service.create_submission,
            conflict_exception=SubmissionConflict,
            logger=logger,
        )


__all__ = ["DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE", "handle_day_close_finalize_text"]
