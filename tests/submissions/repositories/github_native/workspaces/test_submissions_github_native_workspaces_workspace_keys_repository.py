from __future__ import annotations

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    CODING_WORKSPACE_KEY,
    resolve_workspace_key,
)


def test_resolve_workspace_key_maps_day2_day3_code_tasks_to_coding_workspace():
    assert resolve_workspace_key(day_index=2, task_type="code") == CODING_WORKSPACE_KEY
    assert resolve_workspace_key(day_index=3, task_type="code") == CODING_WORKSPACE_KEY
    assert resolve_workspace_key(day_index=2, task_type="DEBUG") == CODING_WORKSPACE_KEY
    assert resolve_workspace_key(day_index=3, task_type="debug") == CODING_WORKSPACE_KEY


def test_resolve_workspace_key_ignores_non_coding_days():
    assert resolve_workspace_key(day_index=1, task_type="code") is None
    assert resolve_workspace_key(day_index=4, task_type="debug") is None
    assert resolve_workspace_key(day_index=2, task_type="design") is None
