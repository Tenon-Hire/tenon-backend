"""Application module for integrations github webhooks handlers workflow run mapping handler workflows."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_models_handler import (
    NON_TERMINAL_WORKFLOW_STATUSES,
    WorkflowRunCompletedEvent,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Simulation,
    Submission,
    Workspace,
)


async def _find_submission_by_workflow_run_id(
    db: AsyncSession, *, workflow_run_id: int, repo_full_name: str
) -> list[Submission]:
    stmt = (
        select(Submission)
        .where(
            Submission.workflow_run_id == str(workflow_run_id),
            Submission.code_repo_path == repo_full_name,
        )
        .with_for_update()
    )
    return list((await db.execute(stmt)).scalars().all())


async def _find_submission_by_head_sha_fallback(
    db: AsyncSession, *, repo_full_name: str, head_sha: str
) -> list[Submission]:
    stmt = (
        select(Submission)
        .where(
            Submission.code_repo_path == repo_full_name,
            Submission.commit_sha == head_sha,
            Submission.last_run_at.is_not(None),
            or_(Submission.workflow_run_id.is_(None), Submission.workflow_run_id == ""),
            or_(
                Submission.workflow_run_status.is_(None),
                Submission.workflow_run_status == "",
                func.lower(Submission.workflow_run_status).in_(
                    NON_TERMINAL_WORKFLOW_STATUSES
                ),
            ),
            Submission.workflow_run_conclusion.is_(None),
            Submission.workflow_run_completed_at.is_(None),
        )
        .with_for_update()
    )
    return list((await db.execute(stmt)).scalars().all())


async def resolve_submission_mapping(
    db: AsyncSession, *, event: WorkflowRunCompletedEvent
) -> tuple[Submission | None, str | None]:
    """Resolve submission mapping."""
    direct_matches = await _find_submission_by_workflow_run_id(
        db, workflow_run_id=event.workflow_run_id, repo_full_name=event.repo_full_name
    )
    if len(direct_matches) == 1:
        return direct_matches[0], "matched_by_workflow_run_id"
    if len(direct_matches) > 1:
        return None, "mapping_ambiguous_workflow_run_id"
    if not event.head_sha:
        return None, "mapping_unmatched"
    fallback_matches = await _find_submission_by_head_sha_fallback(
        db, repo_full_name=event.repo_full_name, head_sha=event.head_sha
    )
    if len(fallback_matches) == 1:
        return fallback_matches[0], "matched_by_repo_head_sha"
    if len(fallback_matches) > 1:
        return None, "mapping_ambiguous_repo_head_sha"
    return None, "mapping_unmatched"


async def company_id_for_submission(
    db: AsyncSession, *, submission: Submission
) -> int | None:
    """Execute company id for submission."""
    stmt = (
        select(Simulation.company_id)
        .join(CandidateSession, CandidateSession.simulation_id == Simulation.id)
        .where(CandidateSession.id == submission.candidate_session_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def workspace_for_submission(
    db: AsyncSession, *, submission: Submission
) -> Workspace | None:
    """Execute workspace for submission."""
    stmt = (
        select(Workspace)
        .where(
            Workspace.candidate_session_id == submission.candidate_session_id,
            Workspace.task_id == submission.task_id,
        )
        .with_for_update()
    )
    return (await db.execute(stmt)).scalar_one_or_none()


__all__ = [
    "company_id_for_submission",
    "resolve_submission_mapping",
    "workspace_for_submission",
]
