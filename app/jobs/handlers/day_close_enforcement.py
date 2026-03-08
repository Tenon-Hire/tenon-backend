from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies.github_native import get_github_client
from app.core.db import async_session_maker
from app.domains import CandidateSession, Task
from app.domains.candidate_sessions import repository as cs_repo
from app.integrations.github import GithubError
from app.repositories.github_native.workspaces import repository as workspace_repo
from app.repositories.github_native.workspaces.workspace_keys import (
    CODING_WORKSPACE_KEY,
)
from app.services.candidate_sessions.day_close_jobs import (
    DAY_CLOSE_ENFORCEMENT_DAY_INDEXES,
    DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
)
from app.services.submissions.payload_validation import CODE_TASK_TYPES

logger = logging.getLogger(__name__)


def _parse_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def _parse_optional_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


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
    github_client,
    *,
    repo_full_name: str,
    workspace_default_branch: str | None,
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


async def handle_day_close_enforcement(payload_json: dict[str, Any]) -> dict[str, Any]:
    candidate_session_id = _parse_positive_int(payload_json.get("candidateSessionId"))
    task_id = _parse_positive_int(payload_json.get("taskId"))
    payload_day_index = _parse_positive_int(payload_json.get("dayIndex"))
    scheduled_cutoff_at = _parse_optional_datetime(payload_json.get("windowEndAt"))

    if (
        candidate_session_id is None
        or task_id is None
        or payload_day_index is None
        or payload_day_index not in DAY_CLOSE_ENFORCEMENT_DAY_INDEXES
    ):
        return {
            "status": "skipped_invalid_payload",
            "candidateSessionId": candidate_session_id,
            "taskId": task_id,
            "dayIndex": payload_day_index,
        }

    now = datetime.now(UTC)
    cutoff_at = scheduled_cutoff_at or now

    async with async_session_maker() as db:
        candidate_session = (
            await db.execute(
                select(CandidateSession)
                .where(CandidateSession.id == candidate_session_id)
                .options(selectinload(CandidateSession.simulation))
            )
        ).scalar_one_or_none()
        if candidate_session is None:
            return {
                "status": "candidate_session_not_found",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": payload_day_index,
            }

        task = (
            await db.execute(
                select(Task).where(
                    Task.id == task_id,
                    Task.simulation_id == candidate_session.simulation_id,
                )
            )
        ).scalar_one_or_none()
        if task is None:
            return {
                "status": "task_not_found",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": payload_day_index,
            }

        task_type = (task.type or "").strip().lower()
        if (
            task.day_index not in DAY_CLOSE_ENFORCEMENT_DAY_INDEXES
            or task_type not in CODE_TASK_TYPES
        ):
            return {
                "status": "skipped_non_code_task",
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "dayIndex": task.day_index,
                "taskType": task_type,
            }

        existing_audit = await cs_repo.get_day_audit(
            db,
            candidate_session_id=candidate_session.id,
            day_index=task.day_index,
        )
        if existing_audit is not None:
            return {
                "status": "no_op_cutoff_exists",
                "candidateSessionId": candidate_session.id,
                "taskId": task.id,
                "dayIndex": task.day_index,
                "cutoffCommitSha": existing_audit.cutoff_commit_sha,
                "cutoffAt": _to_iso_z(existing_audit.cutoff_at),
                "evalBasisRef": existing_audit.eval_basis_ref,
            }

        workspace = await workspace_repo.get_by_session_and_workspace_key(
            db,
            candidate_session_id=candidate_session.id,
            workspace_key=CODING_WORKSPACE_KEY,
        )
        if workspace is None:
            workspace = await workspace_repo.get_by_session_and_task(
                db,
                candidate_session_id=candidate_session.id,
                task_id=task.id,
            )
        if workspace is None or not (workspace.repo_full_name or "").strip():
            raise RuntimeError("day_close_enforcement_workspace_missing_for_coding_day")

        repo_full_name = workspace.repo_full_name.strip()
        github_client = get_github_client()
        revoke_status = await _revoke_repo_write_access(
            github_client,
            repo_full_name=repo_full_name,
            github_username=getattr(candidate_session, "github_username", None),
            candidate_session_id=candidate_session.id,
            day_index=task.day_index,
        )

        default_branch = await _resolve_default_branch(
            github_client,
            repo_full_name=repo_full_name,
            workspace_default_branch=workspace.default_branch,
        )
        branch_payload = await github_client.get_branch(repo_full_name, default_branch)
        cutoff_commit_sha = _extract_head_sha(branch_payload)
        if cutoff_commit_sha is None:
            raise RuntimeError("day_close_enforcement_missing_branch_head_sha")

        eval_basis_ref = f"refs/heads/{default_branch}@cutoff"
        day_audit, created = await cs_repo.create_day_audit_once(
            db,
            candidate_session_id=candidate_session.id,
            day_index=task.day_index,
            cutoff_at=cutoff_at,
            cutoff_commit_sha=cutoff_commit_sha,
            eval_basis_ref=eval_basis_ref,
            commit=True,
        )
        if not created:
            return {
                "status": "no_op_cutoff_exists",
                "candidateSessionId": candidate_session.id,
                "taskId": task.id,
                "dayIndex": task.day_index,
                "cutoffCommitSha": day_audit.cutoff_commit_sha,
                "cutoffAt": _to_iso_z(day_audit.cutoff_at),
                "evalBasisRef": day_audit.eval_basis_ref,
            }

        logger.info(
            "day_close_enforcement_persisted",
            extra={
                "candidateSessionId": candidate_session.id,
                "repoFullName": repo_full_name,
                "cutoffCommitSha": cutoff_commit_sha,
                "cutoffAt": _to_iso_z(day_audit.cutoff_at),
                "evalBasisRef": eval_basis_ref,
                "revokeStatus": revoke_status,
            },
        )
        return {
            "status": "cutoff_persisted",
            "candidateSessionId": candidate_session.id,
            "taskId": task.id,
            "dayIndex": task.day_index,
            "repoFullName": repo_full_name,
            "cutoffCommitSha": day_audit.cutoff_commit_sha,
            "cutoffAt": _to_iso_z(day_audit.cutoff_at),
            "evalBasisRef": day_audit.eval_basis_ref,
            "revokeStatus": revoke_status,
        }


__all__ = ["DAY_CLOSE_ENFORCEMENT_JOB_TYPE", "handle_day_close_enforcement"]
