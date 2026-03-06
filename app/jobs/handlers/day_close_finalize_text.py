from __future__ import annotations

import logging
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import async_session_maker
from app.domains import CandidateSession, Submission, Task
from app.domains.candidate_sessions import service as cs_service
from app.domains.submissions import service_candidate as submission_service
from app.domains.submissions.exceptions import SubmissionConflict
from app.repositories.jobs import repository as jobs_repo
from app.repositories.task_drafts import repository as task_drafts_repo
from app.services.candidate_sessions.day_close_jobs import (
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
    build_day_close_finalize_text_payload,
    day_close_finalize_text_idempotency_key,
)
from app.services.submissions.payload_validation import TEXT_TASK_TYPES
from app.services.task_drafts import NO_DRAFT_AT_CUTOFF_MARKER

logger = logging.getLogger(__name__)


def _parse_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def _parse_optional_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


async def _get_existing_submission(
    db,
    *,
    candidate_session_id: int,
    task_id: int,
) -> Submission | None:
    return (
        await db.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session_id,
                Submission.task_id == task_id,
            )
        )
    ).scalar_one_or_none()


async def handle_day_close_finalize_text(
    payload_json: dict[str, Any],
) -> dict[str, Any]:
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
        candidate_session = (
            await db.execute(
                select(CandidateSession)
                .where(CandidateSession.id == candidate_session_id)
                .options(selectinload(CandidateSession.simulation))
            )
        ).scalar_one_or_none()
        if candidate_session is None:
            return {
                "status": "candidate_session_not_found",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": day_index,
            }

        task = (
            await db.execute(
                select(Task).where(
                    Task.id == task_id,
                    Task.simulation_id == candidate_session.simulation_id,
                )
            )
        ).scalar_one_or_none()
        if task is None:
            return {
                "status": "task_not_found",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": day_index,
            }

        task_type = (task.type or "").strip().lower()
        if task_type not in TEXT_TASK_TYPES:
            return {
                "status": "skipped_non_text_task",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": task.day_index,
                "taskType": task_type,
            }

        task_window = cs_service.compute_task_window(
            candidate_session,
            task,
            now_utc=now,
        )
        window_end_at = task_window.window_end_at
        if window_end_at is None:
            return {
                "status": "skipped_invalid_window",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": task.day_index,
            }
        if now < window_end_at:
            simulation = candidate_session.simulation
            company_id = getattr(simulation, "company_id", None)
            if company_id is None:
                raise RuntimeError("company_id required to reschedule")
            idempotency_key = day_close_finalize_text_idempotency_key(
                candidate_session_id,
                task_id,
            )
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
                idempotency_key=idempotency_key,
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
                "scheduledWindowEndAt": (
                    scheduled_window_end_at.isoformat()
                    if scheduled_window_end_at is not None
                    else None
                ),
            }

        existing_submission = await _get_existing_submission(
            db,
            candidate_session_id=candidate_session_id,
            task_id=task_id,
        )
        draft = await task_drafts_repo.get_by_session_and_task(
            db,
            candidate_session_id=candidate_session_id,
            task_id=task_id,
        )
        if existing_submission is not None:
            if draft is not None and draft.finalized_submission_id is None:
                await task_drafts_repo.mark_finalized(
                    db,
                    draft=draft,
                    finalized_submission_id=existing_submission.id,
                    finalized_at=now,
                    commit=False,
                )
                await db.commit()
            logger.info(
                "Day-close finalize no-op existing submission candidateSessionId=%s taskId=%s dayIndex=%s",
                candidate_session_id,
                task_id,
                task.day_index,
            )
            return {
                "status": "no_op_existing_submission",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": task.day_index,
                "submissionId": existing_submission.id,
            }

        if draft is not None:
            payload = SimpleNamespace(contentText=draft.content_text)
            submission_content_json = draft.content_json
            source = "draft"
        else:
            payload = SimpleNamespace(contentText="")
            submission_content_json = deepcopy(NO_DRAFT_AT_CUTOFF_MARKER)
            source = "no_draft_marker"

        try:
            submission = await submission_service.create_submission(
                db,
                candidate_session,
                task,
                payload,
                now=now,
                content_json=submission_content_json,
            )
        except SubmissionConflict:
            existing_submission = await _get_existing_submission(
                db,
                candidate_session_id=candidate_session_id,
                task_id=task_id,
            )
            if existing_submission is None:
                raise
            if draft is not None and draft.finalized_submission_id is None:
                await task_drafts_repo.mark_finalized(
                    db,
                    draft=draft,
                    finalized_submission_id=existing_submission.id,
                    finalized_at=now,
                    commit=False,
                )
                await db.commit()
            logger.info(
                "Day-close finalize no-op conflict candidateSessionId=%s taskId=%s dayIndex=%s",
                candidate_session_id,
                task_id,
                task.day_index,
            )
            return {
                "status": "no_op_existing_submission",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": task.day_index,
                "submissionId": existing_submission.id,
                "source": source,
            }

        if draft is not None:
            await task_drafts_repo.mark_finalized(
                db,
                draft=draft,
                finalized_submission_id=submission.id,
                finalized_at=now,
                commit=False,
            )
            await db.commit()

        logger.info(
            "Day-close finalize created submission candidateSessionId=%s taskId=%s dayIndex=%s source=%s",
            candidate_session_id,
            task_id,
            task.day_index,
            source,
        )
        return {
            "status": "created_submission",
            "candidateSessionId": candidate_session_id,
            "taskId": task_id,
            "dayIndex": task.day_index,
            "submissionId": submission.id,
            "source": source,
        }


__all__ = ["DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE", "handle_day_close_finalize_text"]
