"""Application module for integrations github actions runner github actions runner result builder service workflows."""

from __future__ import annotations

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_artifacts_service import (
    parse_artifacts,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_backoff_service import (
    apply_backoff,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_model import (
    ActionsRunResult,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_normalize_service import (
    normalize_run,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_runner_types_model import (
    RunnerContext,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_runs_utils import (
    run_cache_key,
)


async def build_result(
    ctx: RunnerContext, repo_full_name: str, run
) -> ActionsRunResult:
    """Build result."""
    base = normalize_run(run)
    parse_fn = getattr(ctx, "_parse_artifacts", None)
    parsed, artifact_error = await (
        parse_fn(repo_full_name, run.id)
        if parse_fn
        else parse_artifacts(ctx.client, ctx.cache, repo_full_name, run.id)
    )
    if parsed:
        base.passed = parsed.passed
        base.failed = parsed.failed
        base.total = parsed.total
        base.stdout = parsed.stdout
        base.stderr = parsed.stderr
        base.raw = base.raw or {}
        base.raw["summary"] = parsed.summary
    elif artifact_error and run.conclusion:
        base.status = "error"
        base.raw = base.raw or {}
        base.raw.setdefault("artifact_error", artifact_error)
        base.stderr = (
            base.stderr
            or "Test results artifact missing or unreadable. Please re-run tests."
        )
    cache_key = run_cache_key(repo_full_name, run.id)
    apply_backoff(ctx.cache, cache_key, base, ctx.poll_interval_seconds)
    return base
