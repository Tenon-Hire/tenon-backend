"""Application module for jobs handlers day close finalize text submission handler workflows."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.task_drafts import NO_DRAFT_AT_CUTOFF_MARKER


async def _mark_draft_finalized_if_pending(
    db, *, draft, submission_id: int, finalized_at
) -> bool:
    if draft is None or draft.finalized_submission_id is not None:
        return False
    await task_drafts_repo.mark_finalized(
        db,
        draft=draft,
        finalized_submission_id=submission_id,
        finalized_at=finalized_at,
        commit=False,
    )
    await db.commit()
    return True


def _payload_for_draft(draft):
    if draft is not None:
        return (
            SimpleNamespace(contentText=draft.content_text),
            draft.content_json,
            "draft",
        )
    return (
        SimpleNamespace(contentText=""),
        deepcopy(NO_DRAFT_AT_CUTOFF_MARKER),
        "no_draft_marker",
    )


async def _finalize_submission_from_cutoff(
    db,
    *,
    candidate_session,
    task,
    candidate_session_id: int,
    task_id: int,
    now,
    get_existing_submission,
    create_submission,
    conflict_exception,
    logger,
) -> dict:
    existing_submission = await get_existing_submission(
        db, candidate_session_id=candidate_session_id, task_id=task_id
    )
    draft = await task_drafts_repo.get_by_session_and_task(
        db, candidate_session_id=candidate_session_id, task_id=task_id
    )
    if existing_submission is not None:
        await _mark_draft_finalized_if_pending(
            db, draft=draft, submission_id=existing_submission.id, finalized_at=now
        )
        await submission_service.progress_after_submission(
            db, candidate_session, now=now
        )
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
    payload, submission_content_json, source = _payload_for_draft(draft)
    try:
        submission = await create_submission(
            db,
            candidate_session,
            task,
            payload,
            now=now,
            content_json=submission_content_json,
        )
    except conflict_exception:
        existing_submission = await get_existing_submission(
            db, candidate_session_id=candidate_session_id, task_id=task_id
        )
        if existing_submission is None:
            raise
        await _mark_draft_finalized_if_pending(
            db, draft=draft, submission_id=existing_submission.id, finalized_at=now
        )
        await submission_service.progress_after_submission(
            db, candidate_session, now=now
        )
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
    await _mark_draft_finalized_if_pending(
        db, draft=draft, submission_id=submission.id, finalized_at=now
    )
    await submission_service.progress_after_submission(db, candidate_session, now=now)
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


__all__ = ["_finalize_submission_from_cutoff"]
