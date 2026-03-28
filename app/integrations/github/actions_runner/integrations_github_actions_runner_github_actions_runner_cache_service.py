"""Application module for integrations github actions runner github actions runner cache service workflows."""

from __future__ import annotations

from collections import OrderedDict

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_cache_artifacts_service import (
    ArtifactCacheMixin,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_cache_runs_service import (
    RunCacheMixin,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_model import (
    ActionsRunResult,
)
from app.integrations.github.artifacts import ParsedTestResults


class ActionsCache(RunCacheMixin, ArtifactCacheMixin):
    """Shared cache for run results and artifacts with simple LRU eviction."""

    def __init__(self, max_entries: int = 128) -> None:
        self.max_entries = max_entries
        self.run_cache: OrderedDict[tuple[str, int], ActionsRunResult] = OrderedDict()
        self.artifact_cache: OrderedDict[
            tuple[str, int, int], tuple[ParsedTestResults | None, str | None]
        ] = OrderedDict()
        self.artifact_list_cache: OrderedDict[
            tuple[str, int], list[dict]
        ] = OrderedDict()
        self.poll_attempts: dict[tuple[str, int], int] = {}
