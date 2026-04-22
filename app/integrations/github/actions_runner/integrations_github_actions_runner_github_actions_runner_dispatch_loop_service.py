"""Application module for integrations github actions runner github actions runner dispatch loop service workflows."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_backoff_service import (
    apply_backoff,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_normalize_service import (
    normalize_run,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_result_builder_service import (
    build_result,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_runner_types_model import (
    RunnerContext,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_runs_utils import (
    is_dispatched_run,
    run_cache_key,
    run_id_set,
)
from app.integrations.github.client import GithubError

logger = logging.getLogger(__name__)


async def dispatch_and_wait(
    ctx: RunnerContext, *, repo_full_name: str, ref: str, inputs: dict[str, Any] | None
) -> Any:
    """Dispatch and wait."""
    dispatch_started_at = datetime.now(UTC)
    dispatch_started_perf = time.perf_counter()
    existing_run_ids: set[int] = set()
    try:
        existing_runs = await ctx.client.list_workflow_runs(
            repo_full_name, ctx.workflow_file, branch=ref, per_page=5
        )
        existing_run_ids = run_id_set(existing_runs)
    except GithubError:
        existing_run_ids = set()
    workflow_file = await ctx._dispatch_with_fallbacks(
        repo_full_name, ref=ref, inputs=inputs
    )
    deadline = asyncio.get_event_loop().time() + ctx.max_poll_seconds
    candidate_run = None
    while asyncio.get_event_loop().time() < deadline:
        runs = await ctx.client.list_workflow_runs(
            repo_full_name, workflow_file, branch=ref, per_page=5
        )
        candidate_run = next(
            (
                run
                for run in runs
                if int(getattr(run, "id", 0) or 0) not in existing_run_ids
                and (run.event or "workflow_dispatch") == "workflow_dispatch"
            ),
            None,
        )
        if candidate_run is None:
            candidate_run = next(
                (run for run in runs if is_dispatched_run(run, dispatch_started_at)),
                None,
            )
        if candidate_run:
            status = (candidate_run.status or "").lower()
            conclusion = (
                (candidate_run.conclusion or "").lower()
                if candidate_run.conclusion
                else None
            )
            logger.info(
                "github_actions_run_observed",
                extra={
                    "repo_full_name": repo_full_name,
                    "run_id": getattr(candidate_run, "id", None),
                    "status": status,
                    "conclusion": conclusion,
                    "elapsed_ms": int(
                        (time.perf_counter() - dispatch_started_perf) * 1000
                    ),
                },
            )
            if conclusion or status == "completed":
                cache_key = run_cache_key(repo_full_name, candidate_run.id)
                result = await build_result(ctx, repo_full_name, candidate_run)
                ctx.cache.cache_run(cache_key, result)
                return result
            cache_key = run_cache_key(repo_full_name, candidate_run.id)
            result = normalize_run(candidate_run, running=True)
            apply_backoff(ctx.cache, cache_key, result, ctx.poll_interval_seconds)
            ctx.cache.cache_run(cache_key, result)
            logger.info(
                "github_actions_run_returning_running",
                extra={
                    "repo_full_name": repo_full_name,
                    "run_id": getattr(candidate_run, "id", None),
                },
            )
            return result
        await asyncio.sleep(ctx.poll_interval_seconds)
    if candidate_run:
        cache_key = run_cache_key(repo_full_name, candidate_run.id)
        result = normalize_run(candidate_run, running=True)
        apply_backoff(ctx.cache, cache_key, result, ctx.poll_interval_seconds)
        ctx.cache.cache_run(cache_key, result)
        logger.info(
            "github_actions_run_timed_out_waiting_for_terminal_state",
            extra={
                "repo_full_name": repo_full_name,
                "run_id": getattr(candidate_run, "id", None),
            },
        )
        return result
    raise GithubError("No workflow run found after dispatch")
