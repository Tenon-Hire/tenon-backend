from __future__ import annotations


class StubGithubClient:
    def __init__(self, *, commits: list[dict] | None = None) -> None:
        self._commits = commits or []
        self.created_blobs: list[tuple[str, str]] = []
        self.created_trees: list[tuple[list[dict], str | None]] = []
        self.created_commits: list[tuple[str, str, list[str]]] = []
        self.updated_refs: list[tuple[str, str, bool]] = []

    async def list_commits(
        self, repo_full_name: str, *, sha: str | None = None, per_page: int = 30
    ) -> list[dict]:
        return list(self._commits)

    async def get_ref(self, repo_full_name: str, ref: str) -> dict:
        return {"ref": ref, "object": {"sha": "head-sha"}}

    async def get_commit(self, repo_full_name: str, commit_sha: str) -> dict:
        return {"sha": commit_sha, "tree": {"sha": "base-tree-sha"}}

    async def create_blob(
        self,
        repo_full_name: str,
        *,
        content: str,
        encoding: str = "utf-8",
    ) -> dict:
        self.created_blobs.append((content, encoding))
        return {"sha": f"blob-{len(self.created_blobs)}"}

    async def create_tree(
        self,
        repo_full_name: str,
        *,
        tree: list[dict],
        base_tree: str | None = None,
    ) -> dict:
        self.created_trees.append((tree, base_tree))
        return {"sha": "new-tree-sha"}

    async def create_commit(
        self,
        repo_full_name: str,
        *,
        message: str,
        tree: str,
        parents: list[str],
    ) -> dict:
        self.created_commits.append((message, tree, parents))
        return {"sha": "new-commit-sha"}

    async def update_ref(
        self,
        repo_full_name: str,
        *,
        ref: str,
        sha: str,
        force: bool = False,
    ) -> dict:
        self.updated_refs.append((ref, sha, force))
        return {"ref": ref, "object": {"sha": sha}}


__all__ = [name for name in globals() if not name.startswith("__")]
