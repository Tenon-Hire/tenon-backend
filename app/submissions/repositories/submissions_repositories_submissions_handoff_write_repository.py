"""Application module for submissions repositories submissions handoff write repository workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Submission


async def create_handoff_submission(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    recording_id: int,
    submitted_at: datetime,
    commit: bool = True,
) -> Submission:
    """Create handoff submission."""
    submission = Submission(
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        recording_id=recording_id,
        submitted_at=submitted_at,
        content_text=None,
        content_json=None,
        code_repo_path=None,
        commit_sha=None,
        checkpoint_sha=None,
        final_sha=None,
        workflow_run_id=None,
        diff_summary_json=None,
        tests_passed=None,
        tests_failed=None,
        test_output=None,
        last_run_at=None,
    )
    db.add(submission)
    if commit:
        await db.commit()
        await db.refresh(submission)
    else:
        await db.flush()
    return submission


async def update_handoff_submission(
    db: AsyncSession,
    *,
    submission: Submission,
    recording_id: int,
    submitted_at: datetime,
    commit: bool = True,
) -> Submission:
    """Update handoff submission."""
    submission.recording_id = recording_id
    submission.submitted_at = submitted_at
    if commit:
        await db.commit()
        await db.refresh(submission)
    else:
        await db.flush()
    return submission
