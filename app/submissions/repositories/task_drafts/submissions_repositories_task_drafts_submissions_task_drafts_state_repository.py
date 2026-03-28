"""Application module for submissions repositories task drafts submissions task drafts state repository workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.submissions.repositories.task_drafts.submissions_repositories_task_drafts_submissions_task_drafts_core_model import (
    TaskDraft,
)


def is_finalized(draft: TaskDraft) -> bool:
    """Return whether finalized."""
    return draft.finalized_at is not None or draft.finalized_submission_id is not None


def apply_draft_values(
    draft: TaskDraft,
    *,
    content_text: str | None,
    content_json: dict[str, Any] | None,
    updated_at: datetime,
) -> None:
    """Apply draft values."""
    draft.content_text = content_text
    draft.content_json = content_json
    draft.updated_at = updated_at
