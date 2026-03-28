"""Application module for integrations github client github client git data client workflows."""

from __future__ import annotations

from .integrations_github_client_github_client_names_utils import split_full_name
from .integrations_github_client_github_client_transport_client import GithubTransport


class GitDataOperations:
    """Represent git data operations data and behavior."""

    transport: GithubTransport

    async def get_ref(self, repo_full_name: str, ref: str) -> dict:
        """Return ref."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/git/ref/{ref}"
        return await self._get_json(path)

    async def get_commit(self, repo_full_name: str, commit_sha: str) -> dict:
        """Return commit."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/git/commits/{commit_sha}"
        return await self._get_json(path)

    async def create_blob(
        self,
        repo_full_name: str,
        *,
        content: str,
        encoding: str = "utf-8",
    ) -> dict:
        """Create blob."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/git/blobs"
        return await self._post_json(
            path,
            json={"content": content, "encoding": encoding},
        )

    async def create_tree(
        self,
        repo_full_name: str,
        *,
        tree: list[dict],
        base_tree: str | None = None,
    ) -> dict:
        """Create tree."""
        owner, repo = split_full_name(repo_full_name)
        payload: dict[str, object] = {"tree": tree}
        if base_tree:
            payload["base_tree"] = base_tree
        path = f"/repos/{owner}/{repo}/git/trees"
        return await self._post_json(path, json=payload)

    async def create_commit(
        self,
        repo_full_name: str,
        *,
        message: str,
        tree: str,
        parents: list[str],
    ) -> dict:
        """Create commit."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/git/commits"
        payload = {"message": message, "tree": tree, "parents": parents}
        return await self._post_json(path, json=payload)

    async def update_ref(
        self,
        repo_full_name: str,
        *,
        ref: str,
        sha: str,
        force: bool = False,
    ) -> dict:
        """Update ref."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/git/refs/{ref}"
        return await self._request("PATCH", path, json={"sha": sha, "force": force})

    async def list_commits(
        self,
        repo_full_name: str,
        *,
        sha: str | None = None,
        per_page: int = 30,
    ) -> list[dict]:
        """Return commits."""
        owner, repo = split_full_name(repo_full_name)
        params: dict[str, str | int] = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        path = f"/repos/{owner}/{repo}/commits"
        data = await self._get_json(path, params=params)
        if not isinstance(data, list):
            return []
        return data
