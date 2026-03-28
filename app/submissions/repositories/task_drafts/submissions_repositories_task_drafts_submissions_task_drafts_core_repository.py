"""Application module for submissions repositories task drafts submissions task drafts core repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories.task_drafts.submissions_repositories_task_drafts_submissions_task_drafts_core_model import (
    TaskDraft,
)
from app.submissions.repositories.task_drafts.submissions_repositories_task_drafts_submissions_task_drafts_state_repository import (
    apply_draft_values,
    is_finalized,
)


class TaskDraftFinalizedError(Exception):
    """Raised when attempting to modify a finalized task draft."""


async def get_by_session_and_task(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
) -> TaskDraft | None:
    """Return by session and task."""
    stmt = select(TaskDraft).where(
        TaskDraft.candidate_session_id == candidate_session_id,
        TaskDraft.task_id == task_id,
    )
    return (
        await db.execute(stmt.execution_options(populate_existing=True))
    ).scalar_one_or_none()


async def upsert_draft(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    content_text: str | None,
    content_json: dict[str, Any] | None,
    updated_at: datetime | None = None,
    commit: bool = True,
) -> TaskDraft:
    """Upsert draft."""
    resolved_updated_at = updated_at or datetime.now(UTC)
    existing = await get_by_session_and_task(
        db,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
    )
    if existing is not None:
        if is_finalized(existing):
            raise TaskDraftFinalizedError()
        apply_draft_values(
            existing,
            content_text=content_text,
            content_json=content_json,
            updated_at=resolved_updated_at,
        )
        if commit:
            await db.commit()
            await db.refresh(existing)
        else:
            await db.flush()
        return existing

    draft = TaskDraft(
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        content_text=content_text,
        content_json=content_json,
        updated_at=resolved_updated_at,
    )

    if commit:
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
        return draft

    db.add(draft)
    await db.flush()
    return draft


async def mark_finalized(
    db: AsyncSession,
    *,
    draft: TaskDraft,
    finalized_submission_id: int,
    finalized_at: datetime | None = None,
    commit: bool = True,
) -> TaskDraft:
    """Mark finalized."""
    if draft.finalized_submission_id is not None:
        return draft

    draft.finalized_submission_id = finalized_submission_id
    draft.finalized_at = finalized_at or datetime.now(UTC)
    if commit:
        await db.commit()
        await db.refresh(draft)
    else:
        await db.flush()
    return draft


__all__ = [
    "TaskDraftFinalizedError",
    "get_by_session_and_task",
    "upsert_draft",
    "mark_finalized",
]
