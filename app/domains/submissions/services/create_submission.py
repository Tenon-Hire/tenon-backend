from __future__ import annotations

# NOTE: Slightly over 50 LOC to keep submission persistence and conflict handling together.
import json
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import CandidateSession, Submission, Task
from app.domains.github_native.actions_runner import ActionsRunResult
from app.domains.github_native.workspaces.workspace import Workspace
from app.domains.submissions.exceptions import SubmissionConflict


async def create_submission(
    db: AsyncSession,
    candidate_session: CandidateSession,
    task: Task,
    payload,
    *,
    now: datetime,
    actions_result: ActionsRunResult | None = None,
    workspace: Workspace | None = None,
    diff_summary_json: str | None = None,
) -> Submission:
    """Persist a submission with conflict handling."""
    tests_passed = tests_failed = last_run_at = commit_sha = workflow_run_id = None
    test_output = None
    if actions_result is not None:
        tests_passed = actions_result.passed
        tests_failed = actions_result.failed
        test_output = json.dumps(actions_result.as_test_output, ensure_ascii=False)
        last_run_at = now
        commit_sha = actions_result.head_sha
        workflow_run_id = str(actions_result.run_id)

    sub = Submission(
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        submitted_at=now,
        content_text=payload.contentText,
        code_repo_path=workspace.repo_full_name if workspace else None,
        commit_sha=commit_sha,
        workflow_run_id=workflow_run_id,
        diff_summary_json=diff_summary_json,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        test_output=test_output,
        last_run_at=last_run_at,
    )
    db.add(sub)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise SubmissionConflict() from exc
    await db.refresh(sub)
    return sub
