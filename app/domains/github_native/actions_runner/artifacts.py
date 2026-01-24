from __future__ import annotations

# NOTE: Exceeds 50 LOC to keep artifact fetching/parsing with cache coordination intact.
from typing import Any

from app.domains.github_native.actions_runner.cache import ActionsCache
from app.domains.github_native.actions_runner.runs import run_cache_key
from app.domains.github_native.artifacts import (
    PREFERRED_ARTIFACT_NAMES,
    ParsedTestResults,
    parse_test_results_zip,
)
from app.domains.github_native.client import GithubClient, GithubError


async def parse_artifacts(
    client: GithubClient, cache: ActionsCache, repo_full_name: str, run_id: int
) -> tuple[ParsedTestResults | None, str | None]:
    list_key = run_cache_key(repo_full_name, run_id)
    artifacts = cache.artifact_list_cache.get(list_key)
    if artifacts is None:
        artifacts = await client.list_artifacts(repo_full_name, run_id)
        cache.cache_artifact_list(list_key, artifacts)

    preferred, others = _partition_artifacts(artifacts)
    found = False
    last_error: str | None = None
    for artifact in preferred + others:
        artifact_id = artifact.get("id")
        if not artifact_id:
            continue
        found = True
        cache_key = (repo_full_name, run_id, int(artifact_id))
        cached = cache.artifact_cache.get(cache_key)
        if cached:
            parsed_cached, cached_error = cached
            if parsed_cached or cached_error:
                return parsed_cached, cached_error
        try:
            content = await client.download_artifact_zip(repo_full_name, int(artifact_id))
        except GithubError:
            last_error = "artifact_download_failed"
            continue
        parsed = parse_test_results_zip(content)
        if parsed:
            cache.cache_artifact_result(cache_key, parsed, None)
            return parsed, None
        last_error = "artifact_corrupt"
        cache.cache_artifact_result(cache_key, None, last_error)
    if found:
        return None, last_error or "artifact_unavailable"
    return None, "artifact_missing"


def _partition_artifacts(artifacts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    preferred: list[dict[str, Any]] = []
    others: list[dict[str, Any]] = []
    for artifact in artifacts:
        if not artifact or artifact.get("expired"):
            continue
        name = str(artifact.get("name") or "").lower()
        (preferred if name in PREFERRED_ARTIFACT_NAMES else others).append(artifact)
    return preferred, others
