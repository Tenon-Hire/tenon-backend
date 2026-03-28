"""Application module for integrations github actions runner github actions runner dispatcher service workflows."""

from __future__ import annotations

from typing import Any

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_dispatch_loop_service import (
    dispatch_and_wait,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_dispatch_service import (
    dispatch_with_fallbacks,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_run_fetcher_service import (
    fetch_run_result,
)


class DispatchRunnerMixin:
    """Async helpers for dispatching and fetching workflow runs."""

    async def dispatch_and_wait(
        self, *, repo_full_name: str, ref: str, inputs: dict[str, Any] | None = None
    ):
        """Dispatch and wait."""
        return await dispatch_and_wait(
            self, repo_full_name=repo_full_name, ref=ref, inputs=inputs
        )

    async def fetch_run_result(self, *, repo_full_name: str, run_id: int):
        """Return run result."""
        return await fetch_run_result(
            self, repo_full_name=repo_full_name, run_id=run_id
        )

    async def _dispatch_with_fallbacks(
        self, repo_full_name: str, *, ref: str, inputs: dict[str, Any] | None
    ):
        return await dispatch_with_fallbacks(
            self.client,
            self._workflow_fallbacks,
            repo_full_name=repo_full_name,
            ref=ref,
            inputs=inputs,
            preferred_workflow=self.workflow_file,
        )
