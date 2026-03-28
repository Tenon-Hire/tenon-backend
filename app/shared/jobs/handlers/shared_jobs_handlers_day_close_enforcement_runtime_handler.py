"""Application module for jobs handlers day close enforcement runtime handler workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_service import (
    DAY_CLOSE_ENFORCEMENT_DAY_INDEXES,
)
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    CODING_WORKSPACE_KEY,
)
from app.submissions.services.submissions_services_submissions_payload_validation_service import (
    CODE_TASK_TYPES,
)


async def handle_day_close_enforcement_impl(
    payload_json: dict,
    *,
    parse_positive_int,
    parse_optional_datetime,
    to_iso_z,
    extract_head_sha,
    resolve_default_branch,
    revoke_repo_write_access,
    async_session_maker,
    get_github_client,
    cs_repo,
    workspace_repo,
    logger,
):
    """Handle day close enforcement impl."""
    candidate_session_id = parse_positive_int(payload_json.get("candidateSessionId"))
    task_id = parse_positive_int(payload_json.get("taskId"))
    payload_day_index = parse_positive_int(payload_json.get("dayIndex"))
    scheduled_cutoff_at = parse_optional_datetime(payload_json.get("windowEndAt"))
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
    cutoff_at = scheduled_cutoff_at or datetime.now(UTC)
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
            db, candidate_session_id=candidate_session.id, day_index=task.day_index
        )
        if existing_audit is not None:
            return {
                "status": "no_op_cutoff_exists",
                "candidateSessionId": candidate_session.id,
                "taskId": task.id,
                "dayIndex": task.day_index,
                "cutoffCommitSha": existing_audit.cutoff_commit_sha,
                "cutoffAt": to_iso_z(existing_audit.cutoff_at),
                "evalBasisRef": existing_audit.eval_basis_ref,
            }
        workspace = await workspace_repo.get_by_session_and_workspace_key(
            db,
            candidate_session_id=candidate_session.id,
            workspace_key=CODING_WORKSPACE_KEY,
        ) or await workspace_repo.get_by_session_and_task(
            db, candidate_session_id=candidate_session.id, task_id=task.id
        )
        if workspace is None or not (workspace.repo_full_name or "").strip():
            raise RuntimeError("day_close_enforcement_workspace_missing_for_coding_day")
        repo_full_name = workspace.repo_full_name.strip()
        github_client = get_github_client()
        revoke_status = await revoke_repo_write_access(
            github_client,
            repo_full_name=repo_full_name,
            github_username=getattr(candidate_session, "github_username", None),
            candidate_session_id=candidate_session.id,
            day_index=task.day_index,
        )
        default_branch = await resolve_default_branch(
            github_client,
            repo_full_name=repo_full_name,
            workspace_default_branch=workspace.default_branch,
        )
        cutoff_commit_sha = extract_head_sha(
            await github_client.get_branch(repo_full_name, default_branch)
        )
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
                "cutoffAt": to_iso_z(day_audit.cutoff_at),
                "evalBasisRef": day_audit.eval_basis_ref,
            }
        logger.info(
            "day_close_enforcement_persisted",
            extra={
                "candidateSessionId": candidate_session.id,
                "repoFullName": repo_full_name,
                "cutoffCommitSha": cutoff_commit_sha,
                "cutoffAt": to_iso_z(day_audit.cutoff_at),
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
            "cutoffAt": to_iso_z(day_audit.cutoff_at),
            "evalBasisRef": day_audit.eval_basis_ref,
            "revokeStatus": revoke_status,
        }


__all__ = ["handle_day_close_enforcement_impl"]
