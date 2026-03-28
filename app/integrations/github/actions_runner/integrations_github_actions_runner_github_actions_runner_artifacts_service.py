"""Application module for integrations github actions runner github actions runner artifacts service workflows."""

from __future__ import annotations

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_artifact_list_service import (
    list_artifacts_with_cache,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_artifact_parser_service import (
    parse_first_artifact,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_artifact_partition_service import (
    partition_artifacts,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_cache_service import (
    ActionsCache,
)
from app.integrations.github.artifacts import ParsedTestResults
from app.integrations.github.client import GithubClient


async def parse_artifacts(
    client: GithubClient, cache: ActionsCache, repo_full_name: str, run_id: int
) -> tuple[ParsedTestResults | None, str | None]:
    """Parse artifacts."""
    artifacts = await list_artifacts_with_cache(client, cache, repo_full_name, run_id)
    preferred, others = partition_artifacts(artifacts)
    parsed, error = await parse_first_artifact(
        client, cache, repo_full_name, run_id, preferred + others
    )
    if parsed:
        return parsed, None
    if error:
        return None, error
    return None, "artifact_missing"
