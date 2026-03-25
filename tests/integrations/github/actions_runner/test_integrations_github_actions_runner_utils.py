from __future__ import annotations

# helper import baseline for restructure-compat
import io
import json
import zipfile
from datetime import UTC, datetime

from app.integrations.github.actions_runner import ActionsRunResult, GithubActionsRunner
from app.integrations.github.artifacts.integrations_github_artifacts_models_model import (
    ParsedTestResults,
)
from app.integrations.github.client import (
    GithubClient,
    GithubError,
    WorkflowRun,
)


class _StubClient(GithubClient):
    def __init__(self):
        super().__init__(base_url="https://api.github.com", token="x")
        self.dispatched = False
        self.run_calls = 0

    async def trigger_workflow_dispatch(self, *args, **kwargs):
        self.dispatched = True

    async def list_workflow_runs(
        self, repo_full_name, workflow_id_or_file, *, branch=None, per_page=5
    ):
        self.run_calls += 1
        now = datetime.now(UTC).isoformat()
        return [
            WorkflowRun(
                id=1,
                status="completed",
                conclusion="success",
                html_url="https://example.com/run/1",
                head_sha="abc123",
                artifact_count=1,
                event="workflow_dispatch",
                created_at=now,
            )
        ]

    async def get_workflow_run(self, repo_full_name, run_id):
        now = datetime.now(UTC).isoformat()
        return WorkflowRun(
            id=run_id,
            status="completed",
            conclusion="failure",
            html_url="https://example.com/run/2",
            head_sha="def456",
            artifact_count=0,
            event="workflow_dispatch",
            created_at=now,
        )

    async def list_artifacts(self, repo_full_name: str, run_id: int):
        return []


__all__ = [name for name in globals() if not name.startswith("__")]
