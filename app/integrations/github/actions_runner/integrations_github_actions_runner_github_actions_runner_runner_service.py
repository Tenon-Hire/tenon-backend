"""Application module for integrations github actions runner github actions runner service workflows."""

from __future__ import annotations

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_cache_service import (
    ActionsCache,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_legacy_accessors_service import (
    RunnerCompatibilityMixin,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_runner_dispatcher_service import (
    DispatchRunnerMixin,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_workflow_fallbacks_service import (
    build_workflow_fallbacks,
)
from app.integrations.github.client import GithubClient


class GithubActionsRunner(DispatchRunnerMixin, RunnerCompatibilityMixin):
    """Helper to dispatch workflow runs and normalize results."""

    def __init__(
        self,
        client: GithubClient,
        *,
        workflow_file: str,
        poll_interval_seconds: float = 2.0,
        max_poll_seconds: float = 120.0,
    ):
        self.client = client
        self.workflow_file = workflow_file
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_seconds = max_poll_seconds
        self.cache = ActionsCache()
        self._workflow_fallbacks = build_workflow_fallbacks(workflow_file)
