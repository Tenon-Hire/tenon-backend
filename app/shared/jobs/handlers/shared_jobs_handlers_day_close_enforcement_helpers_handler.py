"""Application module for jobs handlers day close enforcement helpers handler workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.integrations.github import GithubError
from app.shared.utils.shared_utils_parsing_utils import (
    parse_iso_datetime as _parse_iso_datetime_value,
)
from app.shared.utils.shared_utils_parsing_utils import (
    parse_positive_int as _parse_positive_int_value,
)


def _parse_positive_int(value: Any) -> int | None:
    return _parse_positive_int_value(value)


def _parse_optional_datetime(value: Any) -> datetime | None:
    return _parse_iso_datetime_value(value)


def _to_iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return (
        value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def _extract_head_sha(branch_payload: dict[str, Any]) -> str | None:
    commit = branch_payload.get("commit")
    if not isinstance(commit, dict):
        return None
    sha = commit.get("sha")
    if not isinstance(sha, str):
        return None
    normalized = sha.strip()
    return normalized or None


async def _resolve_default_branch(
    github_client, *, repo_full_name: str, workspace_default_branch: str | None
) -> str:
    if workspace_default_branch and workspace_default_branch.strip():
        return workspace_default_branch.strip()
    repo_payload = await github_client.get_repo(repo_full_name)
    branch = repo_payload.get("default_branch")
    if isinstance(branch, str) and branch.strip():
        return branch.strip()
    return "main"


async def _revoke_repo_write_access(
    github_client,
    *,
    repo_full_name: str,
    github_username: str | None,
    candidate_session_id: int,
    day_index: int,
    logger: logging.Logger,
) -> str:
    username = (github_username or "").strip()
    if not username:
        logger.warning(
            "day_close_enforcement_missing_github_username",
            extra={
                "candidateSessionId": candidate_session_id,
                "repoFullName": repo_full_name,
                "dayIndex": day_index,
            },
        )
        raise RuntimeError("day_close_enforcement_missing_github_username")
    try:
        await github_client.remove_collaborator(repo_full_name, username)
        return "collaborator_removed"
    except GithubError as exc:
        if exc.status_code == 404:
            return "collaborator_not_found"
        raise


__all__ = [
    "_extract_head_sha",
    "_parse_optional_datetime",
    "_parse_positive_int",
    "_resolve_default_branch",
    "_revoke_repo_write_access",
    "_to_iso_z",
]
