"""Application module for integrations github client github client repos client workflows."""

from __future__ import annotations

from .integrations_github_client_github_client_names_utils import split_full_name
from .integrations_github_client_github_client_transport_client import GithubTransport


class RepoOperations:
    """Represent repo operations data and behavior."""

    transport: GithubTransport
    default_org: str | None

    async def generate_repo_from_template(
        self,
        *,
        template_full_name: str,
        new_repo_name: str,
        owner: str | None = None,
        private: bool = True,
    ) -> dict:
        """Generate repo from template."""
        template_owner, template_repo = split_full_name(template_full_name)
        payload = {
            "owner": owner or self.default_org,
            "name": new_repo_name,
            "include_all_branches": False,
            "private": private,
        }
        path = f"/repos/{template_owner}/{template_repo}/generate"
        return await self._request("POST", path, json=payload)

    async def add_collaborator(
        self, repo_full_name: str, username: str, *, permission: str = "push"
    ) -> dict:
        """Add collaborator."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/collaborators/{username}"
        return await self._request("PUT", path, json={"permission": permission})

    async def remove_collaborator(self, repo_full_name: str, username: str) -> dict:
        """Remove collaborator."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/collaborators/{username}"
        return await self._request("DELETE", path, expect_body=False)

    async def archive_repo(self, repo_full_name: str) -> dict:
        """Execute archive repo."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}"
        return await self._request("PATCH", path, json={"archived": True})

    async def delete_repo(self, repo_full_name: str) -> dict:
        """Delete repo."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}"
        return await self._request("DELETE", path, expect_body=False)
