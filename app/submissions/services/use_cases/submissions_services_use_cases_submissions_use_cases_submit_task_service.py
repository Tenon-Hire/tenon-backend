"""Application module for submissions services use cases submissions use cases submit task service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.client import GithubClient
from app.notifications.services import service as notification_service
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.submissions_services_submissions_rate_limits_constants import (
    apply_rate_limit,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_submit_task_runner_service import (
    run_code_submission,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_submit_validation_service import (
    validate_submission_flow,
)


async def submit_task(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    payload,
    github_client: GithubClient,
    actions_runner,
):
    """Submit task."""
    apply_rate_limit(candidate_session.id, "submit")
    validation_result = await validate_submission_flow(
        db, candidate_session, task_id, payload
    )
    if len(validation_result) == 2:
        task, content_json = validation_result
        task_list = None
    else:
        task, content_json, task_list = validation_result
    now = shared_utcnow()
    actions_result = diff_summary_json = workspace = None
    if submission_service.is_code_task(task):
        actions_result, diff_summary_json, workspace = await run_code_submission(
            db=db,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            task_day_index=getattr(task, "day_index", None),
            task_type=getattr(task, "type", None),
            payload=payload,
            github_client=github_client,
            actions_runner=actions_runner,
        )
    submission = await submission_service.create_submission(
        db,
        candidate_session,
        task,
        payload,
        now=now,
        content_json=content_json,
        actions_result=actions_result,
        workspace=workspace,
        diff_summary_json=diff_summary_json,
    )
    draft_finalized = False
    draft = await task_drafts_repo.get_by_session_and_task(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    if draft is not None and draft.finalized_submission_id is None:
        await task_drafts_repo.mark_finalized(
            db,
            draft=draft,
            finalized_submission_id=submission.id,
            finalized_at=now,
            commit=False,
        )
        draft_finalized = True
    completed, total, is_complete = await submission_service.progress_after_submission(
        db, candidate_session, now=now, tasks=task_list
    )
    if is_complete:
        await notification_service.enqueue_candidate_completed_notification(
            db,
            candidate_session_id=candidate_session.id,
            trial_id=candidate_session.trial_id,
            commit=True,
        )
    if draft_finalized:
        await db.commit()
    return task, submission, completed, total, is_complete
