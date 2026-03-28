from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Submission,
    Task,
)


async def create_submission(
    session: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task: Task,
    content_text: str | None = None,
    content_json: dict[str, object] | None = None,
    submitted_at: datetime | None = None,
    tests_passed: int | None = None,
    tests_failed: int | None = None,
    test_output: str | None = None,
    code_repo_path: str | None = None,
    last_run_at: datetime | None = None,
    commit_sha: str | None = None,
    workflow_run_id: str | None = None,
    workflow_run_attempt: int | None = None,
    workflow_run_status: str | None = None,
    workflow_run_conclusion: str | None = None,
    workflow_run_completed_at: datetime | None = None,
    diff_summary_json: str | None = None,
    recording_id: int | None = None,
) -> Submission:
    submission = Submission(
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        recording_id=recording_id,
        submitted_at=submitted_at or datetime.now(UTC),
        content_text=content_text,
        content_json=content_json,
        code_repo_path=code_repo_path,
        commit_sha=commit_sha,
        workflow_run_id=workflow_run_id,
        workflow_run_attempt=workflow_run_attempt,
        workflow_run_status=workflow_run_status,
        workflow_run_conclusion=workflow_run_conclusion,
        workflow_run_completed_at=workflow_run_completed_at,
        diff_summary_json=diff_summary_json,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        test_output=test_output,
        last_run_at=last_run_at,
    )
    session.add(submission)
    await session.flush()
    return submission
