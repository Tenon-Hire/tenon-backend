"""Application module for integrations github actions runner github actions runner backoff service workflows."""

from __future__ import annotations

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_cache_service import (
    ActionsCache,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_model import (
    ActionsRunResult,
)


def apply_backoff(
    cache: ActionsCache,
    key: tuple[str, int],
    result: ActionsRunResult,
    base_interval_seconds: float,
) -> None:
    """Apply backoff."""
    if not cache.is_terminal(result) and result.status == "running":
        attempt = cache.poll_attempts.get(key, 0) + 1
        cache.poll_attempts[key] = attempt
        base_ms = int(base_interval_seconds * 1000)
        result.poll_after_ms = min(base_ms * (2 ** (attempt - 1)), 15000)
    else:
        cache.poll_attempts.pop(key, None)
        result.poll_after_ms = None
