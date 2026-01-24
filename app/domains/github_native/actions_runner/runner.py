from __future__ import annotations

# NOTE: Exceeds 50 LOC to keep runner orchestration cohesive for dispatch/poll/cache.
import asyncio
from datetime import UTC, datetime
from typing import Any

from app.domains.github_native.actions_runner.artifacts import parse_artifacts
from app.domains.github_native.actions_runner.backoff import apply_backoff
from app.domains.github_native.actions_runner.cache import ActionsCache
from app.domains.github_native.actions_runner.dispatch import dispatch_with_fallbacks
from app.domains.github_native.actions_runner.models import ActionsRunResult
from app.domains.github_native.actions_runner.normalize import normalize_run
from app.domains.github_native.actions_runner.runs import (
    is_dispatched_run,
    run_cache_key,
)
from app.domains.github_native.client import GithubClient, GithubError


class GithubActionsRunner:
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
        self._workflow_fallbacks = list(
            dict.fromkeys(
                [workflow_file, "tenon-ci.yml", ".github/workflows/tenon-ci.yml"]
            )
        )

    async def dispatch_and_wait(
        self, *, repo_full_name: str, ref: str, inputs: dict[str, Any] | None = None
    ) -> ActionsRunResult:
        dispatch_started_at = datetime.now(UTC)
        workflow_file = await self._dispatch_with_fallbacks(
            repo_full_name,
            ref=ref,
            inputs=inputs,
        )
        deadline = asyncio.get_event_loop().time() + self.max_poll_seconds
        candidate_run = None
        while asyncio.get_event_loop().time() < deadline:
            runs = await self.client.list_workflow_runs(
                repo_full_name, workflow_file, branch=ref, per_page=5
            )
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
                if conclusion or status == "completed":
                    run_id = candidate_run.id
                    cache_key = run_cache_key(repo_full_name, run_id)
                    result = await self._build_result(repo_full_name, candidate_run)
                    self.cache.cache_run(cache_key, result)
                    return result
            await asyncio.sleep(self.poll_interval_seconds)

        if candidate_run:
            run_id = candidate_run.id
            cache_key = run_cache_key(repo_full_name, run_id)
            result = normalize_run(candidate_run, running=True)
            apply_backoff(self.cache, cache_key, result, self.poll_interval_seconds)
            self.cache.cache_run(cache_key, result)
            return result
        raise GithubError("No workflow run found after dispatch")

    async def fetch_run_result(
        self, *, repo_full_name: str, run_id: int
    ) -> ActionsRunResult:
        cache_key = run_cache_key(repo_full_name, run_id)
        cached = self.cache.run_cache.get(cache_key)
        if cached and self.cache.is_terminal(cached):
            return cached
        run = await self.client.get_workflow_run(repo_full_name, run_id)
        result = await self._build_result(repo_full_name, run)
        self.cache.cache_run(cache_key, result)
        return result

    async def _build_result(self, repo_full_name: str, run) -> ActionsRunResult:
        base = self._normalize_run(run)
        parsed, artifact_error = await self._parse_artifacts(repo_full_name, run.id)
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
        apply_backoff(self.cache, cache_key, base, self.poll_interval_seconds)
        return base

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

    # Legacy helper methods preserved for tests/compatibility
    def _normalize_run(
        self, run, *, timed_out: bool = False, running: bool = False
    ) -> ActionsRunResult:
        return normalize_run(run, timed_out=timed_out, running=running)

    def _is_dispatched_run(self, run, dispatch_started_at):
        return is_dispatched_run(run, dispatch_started_at)

    @staticmethod
    def _run_cache_key(repo_full_name: str, run_id: int) -> tuple[str, int]:
        return run_cache_key(repo_full_name, run_id)

    def _cache_run_result(self, key: tuple[str, int], result: ActionsRunResult) -> None:
        self.cache.cache_run(key, result)

    def _cache_artifact_result(self, key, parsed, error):
        self.cache.cache_artifact_result(key, parsed, error)

    def _cache_artifact_list(self, key, artifacts):
        self.cache.cache_artifact_list(key, artifacts)

    def _apply_backoff(self, key, result):
        apply_backoff(self.cache, key, result, self.poll_interval_seconds)

    async def _parse_artifacts(self, repo_full_name: str, run_id: int):
        return await parse_artifacts(self.client, self.cache, repo_full_name, run_id)

    @property
    def _run_cache(self):
        return self.cache.run_cache

    @property
    def _artifact_cache(self):
        return self.cache.artifact_cache

    @property
    def _artifact_list_cache(self):
        return self.cache.artifact_list_cache

    @property
    def _poll_attempts(self):
        return self.cache.poll_attempts

    @property
    def _max_cache_entries(self):
        return self.cache.max_entries

    @_max_cache_entries.setter
    def _max_cache_entries(self, value: int):
        self.cache.max_entries = value
