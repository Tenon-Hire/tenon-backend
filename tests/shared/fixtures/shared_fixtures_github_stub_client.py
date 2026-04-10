from __future__ import annotations

import base64


class StubGithubClient:
    _workflow_text = "\n".join(
        [
            "uses: actions/upload-artifact@v4",
            "name: winoe-test-results",
            "path: artifacts/winoe-test-results.json",
        ]
    )

    async def generate_repo_from_template(
        self,
        *,
        template_full_name: str,
        new_repo_name: str,
        owner=None,
        private=True,
    ):
        owner_prefix = owner or "org"
        return {
            "full_name": f"{owner_prefix}/{new_repo_name}",
            "id": 999,
            "default_branch": "main",
        }

    async def add_collaborator(
        self, repo_full_name: str, username: str, *, permission: str = "push"
    ):
        return {"ok": True}

    async def get_branch(self, repo_full_name: str, branch: str):
        return {"commit": {"sha": "base-sha-123"}}

    async def get_repo(self, repo_full_name: str):
        return {"default_branch": "main"}

    async def get_file_contents(
        self, repo_full_name: str, file_path: str, *, ref: str | None = None
    ):
        encoded = base64.b64encode(self._workflow_text.encode("utf-8")).decode("ascii")
        return {"content": encoded, "encoding": "base64"}

    async def get_compare(self, repo_full_name: str, base: str, head: str):
        return {"ahead_by": 0, "behind_by": 0, "total_commits": 0, "files": []}

    async def list_commits(
        self, repo_full_name: str, *, sha: str | None = None, per_page: int = 30
    ):
        return []

    async def get_ref(self, repo_full_name: str, ref: str):
        return {"ref": ref, "object": {"sha": "head-sha-123"}}

    async def get_commit(self, repo_full_name: str, commit_sha: str):
        return {"sha": commit_sha, "tree": {"sha": "tree-sha-123"}}

    async def create_blob(
        self, repo_full_name: str, *, content: str, encoding: str = "utf-8"
    ):
        return {"sha": f"blob-{len(content.encode('utf-8'))}"}

    async def create_tree(
        self, repo_full_name: str, *, tree: list[dict], base_tree: str | None = None
    ):
        return {"sha": "tree-sha-456", "tree": tree, "base_tree": base_tree}

    async def create_commit(
        self, repo_full_name: str, *, message: str, tree: str, parents: list[str]
    ):
        return {"sha": "precommit-sha-789", "message": message, "tree": tree}

    async def update_ref(
        self, repo_full_name: str, *, ref: str, sha: str, force: bool = False
    ):
        return {"ref": ref, "object": {"sha": sha}, "force": force}
