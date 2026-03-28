"""Application module for integrations github actions runner github actions runner run fetcher service workflows."""

from __future__ import annotations

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_model import (
    ActionsRunResult,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_result_builder_service import (
    build_result,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_runner_types_model import (
    RunnerContext,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_runs_utils import (
    run_cache_key,
)


async def fetch_run_result(
    ctx: RunnerContext, *, repo_full_name: str, run_id: int
) -> ActionsRunResult:
    """Return run result."""
    cache_key = run_cache_key(repo_full_name, run_id)
    cached = ctx.cache.run_cache.get(cache_key)
    if cached and ctx.cache.is_terminal(cached):
        return cached
    run = await ctx.client.get_workflow_run(repo_full_name, run_id)
    result = await build_result(ctx, repo_full_name, run)
    ctx.cache.cache_run(cache_key, result)
    return result
