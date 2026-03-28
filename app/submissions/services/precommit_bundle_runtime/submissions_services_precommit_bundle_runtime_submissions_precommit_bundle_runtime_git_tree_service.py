"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime git tree service workflows."""

from __future__ import annotations

from app.shared.utils.shared_utils_errors_utils import ApiError


async def resolve_head_and_tree_sha(
    github_client,
    *,
    repo_full_name: str,
    branch_name: str,
) -> tuple[str, str]:
    """Resolve head and tree sha."""
    head_ref = await github_client.get_ref(repo_full_name, f"heads/{branch_name}")
    head_sha = ((head_ref.get("object") or {}).get("sha") or "").strip()
    if not head_sha:
        raise ApiError(
            status_code=500,
            detail="Unable to resolve repository head SHA for precommit apply.",
            error_code="PRECOMMIT_REPO_HEAD_MISSING",
            details={"repoFullName": repo_full_name, "branch": branch_name},
        )

    head_commit = await github_client.get_commit(repo_full_name, head_sha)
    base_tree_sha = ((head_commit.get("tree") or {}).get("sha") or "").strip()
    if not base_tree_sha:
        raise ApiError(
            status_code=500,
            detail="Unable to resolve repository tree for precommit apply.",
            error_code="PRECOMMIT_REPO_TREE_MISSING",
            details={"repoFullName": repo_full_name, "headSha": head_sha},
        )
    return head_sha, base_tree_sha


async def build_tree_entries(
    github_client, *, repo_full_name: str, changes, bundle_id: int
):
    """Build tree entries."""
    tree_entries: list[dict[str, object]] = []
    for change in changes:
        if change.delete:
            tree_entries.append(
                {"path": change.path, "mode": "100644", "type": "blob", "sha": None}
            )
            continue

        blob = await github_client.create_blob(
            repo_full_name,
            content=change.content or "",
            encoding="utf-8",
        )
        blob_sha = (blob.get("sha") or "").strip()
        if not blob_sha:
            raise ApiError(
                status_code=500,
                detail="Failed to create precommit bundle blob.",
                error_code="PRECOMMIT_BLOB_CREATE_FAILED",
                details={"bundleId": bundle_id, "path": change.path},
            )
        tree_entries.append(
            {
                "path": change.path,
                "mode": "100755" if change.executable else "100644",
                "type": "blob",
                "sha": blob_sha,
            }
        )
    return tree_entries


__all__ = ["build_tree_entries", "resolve_head_and_tree_sha"]
