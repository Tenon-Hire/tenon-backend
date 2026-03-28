"""Application module for jobs handlers github workflow artifact parse persist handler workflows."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.shared.database.shared_database_models_model import Submission
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)

from .shared_jobs_handlers_github_workflow_artifact_parse_payload_handler import (
    ArtifactParsePayload,
)


async def persist_artifact_parse_result(
    *,
    async_session_maker: Any,
    payload: ArtifactParsePayload,
    build_actions_runner: Callable[[], tuple[Any, Any]],
    normalized_text: Callable[[Any], str | None],
) -> dict[str, Any]:
    """Execute persist artifact parse result."""
    async with async_session_maker() as db:
        submission = (
            await db.execute(
                select(Submission)
                .where(Submission.id == payload.submission_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if submission is None:
            return {
                "status": "submission_not_found",
                "submissionId": payload.submission_id,
                "workflowRunId": payload.workflow_run_id,
                "repoFullName": payload.repo_full_name,
            }
        if (
            payload.payload_candidate_session_id is not None
            and payload.payload_candidate_session_id != submission.candidate_session_id
        ):
            return {
                "status": "skipped_candidate_session_mismatch",
                "submissionId": submission.id,
                "candidateSessionId": submission.candidate_session_id,
                "payloadCandidateSessionId": payload.payload_candidate_session_id,
                "workflowRunId": payload.workflow_run_id,
            }
        if (
            payload.payload_task_id is not None
            and payload.payload_task_id != submission.task_id
        ):
            return {
                "status": "skipped_task_mismatch",
                "submissionId": submission.id,
                "taskId": submission.task_id,
                "payloadTaskId": payload.payload_task_id,
                "workflowRunId": payload.workflow_run_id,
            }
        stored_workflow_run_id = (submission.workflow_run_id or "").strip()
        if stored_workflow_run_id and stored_workflow_run_id != str(
            payload.workflow_run_id
        ):
            return {
                "status": "skipped_workflow_run_mismatch",
                "submissionId": submission.id,
                "workflowRunId": payload.workflow_run_id,
                "storedWorkflowRunId": stored_workflow_run_id,
            }

        workspace = (
            await db.execute(
                select(Workspace)
                .where(
                    Workspace.candidate_session_id == submission.candidate_session_id,
                    Workspace.task_id == submission.task_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()

        runner, github_client = build_actions_runner()
        try:
            result = await runner.fetch_run_result(
                repo_full_name=payload.repo_full_name, run_id=payload.workflow_run_id
            )
        finally:
            await github_client.aclose()

        output_json = json.dumps(result.as_test_output, ensure_ascii=False)
        normalized_conclusion = normalized_text(result.conclusion)
        normalized_conclusion = (
            normalized_conclusion.lower() if normalized_conclusion else None
        )

        submission.tests_passed = result.passed
        submission.tests_failed = result.failed
        submission.test_output = output_json
        submission.workflow_run_id = str(result.run_id)
        submission.workflow_run_status = "completed"
        submission.workflow_run_conclusion = normalized_conclusion
        if payload.workflow_run_attempt is not None:
            submission.workflow_run_attempt = payload.workflow_run_attempt
        if payload.workflow_completed_at is not None:
            submission.workflow_run_completed_at = payload.workflow_completed_at
            submission.last_run_at = payload.workflow_completed_at
        elif submission.last_run_at is None:
            submission.last_run_at = datetime.now(UTC).replace(microsecond=0)
        if result.head_sha:
            submission.commit_sha = result.head_sha

        if workspace is not None:
            workspace.last_workflow_run_id = str(result.run_id)
            workspace.last_workflow_conclusion = normalized_conclusion
            workspace.latest_commit_sha = result.head_sha
            workspace.last_test_summary_json = output_json

        await db.commit()
        return {
            "status": "parsed_and_persisted",
            "submissionId": submission.id,
            "candidateSessionId": submission.candidate_session_id,
            "taskId": submission.task_id,
            "workflowRunId": result.run_id,
            "workspaceId": workspace.id if workspace is not None else None,
        }
