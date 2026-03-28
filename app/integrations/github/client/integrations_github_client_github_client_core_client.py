"""Application module for integrations github client github client core client workflows."""

from __future__ import annotations

from .integrations_github_client_github_client_artifacts_client import (
    ArtifactOperations,
)
from .integrations_github_client_github_client_compat_client import CompatOperations
from .integrations_github_client_github_client_content_client import ContentOperations
from .integrations_github_client_github_client_git_data_client import GitDataOperations
from .integrations_github_client_github_client_repos_client import RepoOperations
from .integrations_github_client_github_client_transport_client import GithubTransport
from .integrations_github_client_github_client_workflows_client import (
    WorkflowOperations,
)


class GithubClient(
    RepoOperations,
    WorkflowOperations,
    ContentOperations,
    GitDataOperations,
    ArtifactOperations,
    CompatOperations,
):
    """Represent github client data and behavior."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        default_org: str | None = None,
        transport=None,
    ):
        self.transport = GithubTransport(
            base_url=base_url,
            token=token,
            transport=transport,
        )
        self.default_org = default_org

    async def aclose(self) -> None:
        """Execute aclose."""
        await self.transport.aclose()
