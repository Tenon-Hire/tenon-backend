"""Application module for integrations github actions runner github actions runner legacy accessors service workflows."""

from __future__ import annotations

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_legacy_cache_service import (
    LegacyCacheMixin,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_legacy_results_service import (
    LegacyResultMixin,
)


class RunnerCompatibilityMixin(LegacyResultMixin, LegacyCacheMixin):
    """Compatibility helpers preserved for tests and call sites."""
