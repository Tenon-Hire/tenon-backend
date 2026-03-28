"""Application module for submissions services use cases submissions use cases codespace validations service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.shared.database.shared_database_models_model import CandidateSession
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)


async def validate_codespace_request(
    db: AsyncSession, candidate_session: CandidateSession, task_id: int
):
    """Validate codespace request."""
    task_list, _, current, *_ = await cs_service.progress_snapshot(
        db, candidate_session
    )
    task = next((item for item in task_list if item.id == task_id), None)
    if task is None and getattr(current, "id", None) == task_id:
        task = current
    if task is None:
        task = await submission_service.load_task_or_404(db, task_id)
        submission_service.ensure_task_belongs(task, candidate_session)
    cs_service.require_active_window(candidate_session, task)
    submission_service.ensure_in_order(current, task_id)
    submission_service.validate_run_allowed(task)
    return task


__all__ = ["validate_codespace_request"]
