"""Application module for submissions services use cases submissions use cases submit validation service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.shared.database.shared_database_models_model import CandidateSession
from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    SubmissionConflict,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_day_flow_gate_service import (
    ensure_day_flow_open,
)


async def validate_submission_flow(
    db: AsyncSession,
    candidate_session: CandidateSession,
    task_id: int,
    payload,
):
    """Validate submission flow."""
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    cs_service.require_active_window(candidate_session, task)
    await ensure_day_flow_open(db, candidate_session=candidate_session, task=task)
    task_list, completed_ids, current_task, *_ = await cs_service.progress_snapshot(
        db, candidate_session
    )
    if task_id in completed_ids:
        raise SubmissionConflict()
    submission_service.ensure_in_order(current_task, task_id)
    content_json = submission_service.validate_submission_payload(task, payload)
    return task, content_json, task_list
