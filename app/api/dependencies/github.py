from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.services.github import GithubClient
from app.services.github.actions import GithubActionsRunner


def get_github_client() -> GithubClient:
    """Default GitHub client dependency."""
    return GithubClient(
        base_url=settings.github.GITHUB_API_BASE,
        token=settings.github.GITHUB_TOKEN,
        default_org=settings.github.GITHUB_ORG or None,
    )


def get_actions_runner(
    github_client: Annotated[GithubClient, Depends(get_github_client)],
) -> GithubActionsRunner:
    """Actions runner dependency with configured workflow file."""
    return GithubActionsRunner(
        github_client,
        workflow_file=settings.github.GITHUB_ACTIONS_WORKFLOW_FILE,
        poll_interval_seconds=2.0,
        max_poll_seconds=90.0,
    )
