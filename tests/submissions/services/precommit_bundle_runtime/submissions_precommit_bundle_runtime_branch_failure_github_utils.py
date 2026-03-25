from __future__ import annotations

from app.integrations.github.client import GithubError
from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_stub_github_client_utils import (
    StubGithubClient,
)


class _BranchFailureGithub(StubGithubClient):
    def __init__(
        self,
        *,
        ref_sha: str = "head-sha",
        tree_sha: str = "base-tree-sha",
        blob_sha: str = "blob-1",
        commit_sha: str = "new-commit-sha",
        raise_update: GithubError | None = None,
        commits: list[dict] | None = None,
        commits_by_call: list[list[dict]] | None = None,
    ) -> None:
        super().__init__(commits=commits)
        self._ref_sha = ref_sha
        self._tree_sha = tree_sha
        self._blob_sha = blob_sha
        self._commit_sha = commit_sha
        self._raise_update = raise_update
        self._commits_by_call = commits_by_call
        self._commit_lookup_calls = 0

    async def list_commits(
        self, repo_full_name: str, *, sha: str | None = None, per_page: int = 30
    ) -> list[dict]:
        self._commit_lookup_calls += 1
        if self._commits_by_call is not None:
            idx = self._commit_lookup_calls - 1
            if idx < len(self._commits_by_call):
                return list(self._commits_by_call[idx])
            return []
        return await super().list_commits(repo_full_name, sha=sha, per_page=per_page)

    async def get_ref(self, repo_full_name: str, ref: str) -> dict:
        return {"ref": ref, "object": {"sha": self._ref_sha}}

    async def get_commit(self, repo_full_name: str, commit_sha: str) -> dict:
        return {"sha": commit_sha, "tree": {"sha": self._tree_sha}}

    async def create_blob(
        self,
        repo_full_name: str,
        *,
        content: str,
        encoding: str = "utf-8",
    ) -> dict:
        self.created_blobs.append((content, encoding))
        return {"sha": self._blob_sha}

    async def create_tree(
        self,
        repo_full_name: str,
        *,
        tree: list[dict],
        base_tree: str | None = None,
    ) -> dict:
        return {"sha": "new-tree-sha"}

    async def create_commit(
        self,
        repo_full_name: str,
        *,
        message: str,
        tree: str,
        parents: list[str],
    ) -> dict:
        return {"sha": self._commit_sha}

    async def update_ref(
        self,
        repo_full_name: str,
        *,
        ref: str,
        sha: str,
        force: bool = False,
    ) -> dict:
        if self._raise_update is not None:
            raise self._raise_update
        return {"ref": ref, "object": {"sha": sha}}


__all__ = [name for name in globals() if not name.startswith("__")]
