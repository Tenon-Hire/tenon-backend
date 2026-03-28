"""Application module for submissions repositories github native workspaces submissions github native workspaces workspace keys repository workflows."""

from __future__ import annotations

from app.tasks.repositories.tasks_repositories_tasks_repository_model import Task

CODING_WORKSPACE_KEY = "coding"
_CODING_TASK_TYPES = {"code", "debug"}
_CODING_DAY_INDEXES = {2, 3}


def resolve_workspace_key(
    *, day_index: int | None, task_type: str | None
) -> str | None:
    """Resolve workspace key."""
    normalized_type = (task_type or "").lower()
    if day_index in _CODING_DAY_INDEXES and normalized_type in _CODING_TASK_TYPES:
        return CODING_WORKSPACE_KEY
    return None


def resolve_workspace_key_for_task(task: Task) -> str | None:
    """Resolve workspace key for task."""
    return resolve_workspace_key(
        day_index=getattr(task, "day_index", None),
        task_type=getattr(task, "type", None),
    )
