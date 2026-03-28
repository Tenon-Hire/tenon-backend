from __future__ import annotations

from types import SimpleNamespace

from app.integrations.github.webhooks.handlers import (
    integrations_github_webhooks_handlers_workflow_run_updates_handler as updates_handler,
)


def test_apply_workspace_completion_returns_false_when_no_fields_change():
    workspace = SimpleNamespace(
        last_workflow_run_id="12345",
        last_workflow_conclusion="success",
        latest_commit_sha="commit-sha",
    )
    event = SimpleNamespace(
        workflow_run_id=12345,
        conclusion="success",
        head_sha=None,
    )

    changed = updates_handler.apply_workspace_completion(workspace, event=event)

    assert changed is False
    assert workspace.last_workflow_run_id == "12345"
    assert workspace.last_workflow_conclusion == "success"
    assert workspace.latest_commit_sha == "commit-sha"
