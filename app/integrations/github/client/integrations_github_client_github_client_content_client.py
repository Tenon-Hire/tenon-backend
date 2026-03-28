"""Application module for integrations github client github client content client workflows."""

from __future__ import annotations

from .integrations_github_client_github_client_names_utils import split_full_name
from .integrations_github_client_github_client_transport_client import GithubTransport


class ContentOperations:
    """Represent content operations data and behavior."""

    transport: GithubTransport

    async def get_branch(self, repo_full_name: str, branch: str) -> dict:
        """Return branch."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/branches/{branch}"
        return await self._get_json(path)

    async def get_repo(self, repo_full_name: str) -> dict:
        """Return repo."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}"
        return await self._get_json(path)

    async def get_file_contents(
        self, repo_full_name: str, file_path: str, *, ref: str | None = None
    ) -> dict:
        """Return file contents."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/contents/{file_path}"
        params = {"ref": ref} if ref else None
        return await self._get_json(path, params=params)

    async def get_compare(self, repo_full_name: str, base: str, head: str) -> dict:
        """Return compare."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/compare/{base}...{head}"
        return await self._get_json(path)
