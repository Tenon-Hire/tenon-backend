"""Application module for candidates routes candidate sessions routes candidates candidate sessions routes responses current task routes workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from app.candidates.candidate_sessions import services as cs_service
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CurrentTaskResponse,
    CurrentTaskWindow,
    ProgressSummary,
)
from app.tasks.schemas.tasks_schemas_tasks_public_schema import TaskPublic


def _resolve_cutoff_fields(day_audit) -> tuple[str | None, datetime | None]:
    if day_audit is None:
        return None, None
    cutoff_commit_sha = getattr(day_audit, "cutoff_commit_sha", None)
    cutoff_at = getattr(day_audit, "cutoff_at", None)
    if isinstance(cutoff_at, datetime) and cutoff_at.tzinfo is None:
        cutoff_at = cutoff_at.replace(tzinfo=UTC)
    return cutoff_commit_sha, cutoff_at


def build_current_task_response(
    cs,
    current_task,
    completed_ids,
    completed,
    total,
    is_complete,
    *,
    day_audit=None,
    now_utc,
):
    """Build current task response."""
    current_window = None
    if not is_complete and current_task is not None:
        task_window = cs_service.compute_task_window(cs, current_task, now_utc=now_utc)
        if (
            task_window.window_start_at is not None
            and task_window.window_end_at is not None
        ):
            current_window = CurrentTaskWindow(
                windowStartAt=task_window.window_start_at,
                windowEndAt=task_window.window_end_at,
                nextOpenAt=task_window.next_open_at,
                isOpen=task_window.is_open,
                now=task_window.now,
            )
    cutoff_commit_sha, cutoff_at = _resolve_cutoff_fields(day_audit)
    return CurrentTaskResponse(
        candidateSessionId=cs.id,
        status=cs.status,
        currentDayIndex=None if is_complete else current_task.day_index,
        currentTask=None
        if is_complete
        else TaskPublic(
            id=current_task.id,
            dayIndex=current_task.day_index,
            title=current_task.title,
            type=current_task.type,
            description=current_task.description,
            cutoffCommitSha=cutoff_commit_sha,
            cutoffAt=cutoff_at,
        ),
        completedTaskIds=sorted(completed_ids),
        progress=ProgressSummary(completed=completed, total=total),
        isComplete=is_complete,
        currentWindow=current_window,
    )
