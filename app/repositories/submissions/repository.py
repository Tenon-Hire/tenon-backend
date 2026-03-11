from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import Simulation, Submission


async def find_duplicate(
    db: AsyncSession, candidate_session_id: int, task_id: int
) -> bool:
    """Return True if a submission already exists for candidate/task."""
    dup_stmt = select(Submission.id).where(
        Submission.candidate_session_id == candidate_session_id,
        Submission.task_id == task_id,
    )
    dup_res = await db.execute(dup_stmt)
    return dup_res.scalar_one_or_none() is not None


async def simulation_template(db: AsyncSession, simulation_id: int) -> str | None:
    """Return a stable scenario key for a simulation."""
    stmt = select(
        Simulation.scenario_template,
        Simulation.focus,
    ).where(Simulation.id == simulation_id)
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        return None
    scenario_template, focus = row
    return scenario_template or focus


async def get_by_candidate_session_task(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    for_update: bool = False,
) -> Submission | None:
    stmt = select(Submission).where(
        Submission.candidate_session_id == candidate_session_id,
        Submission.task_id == task_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def create_handoff_submission(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    recording_id: int,
    submitted_at: datetime,
    commit: bool = True,
) -> Submission:
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
    submission.recording_id = recording_id
    submission.submitted_at = submitted_at
    if commit:
        await db.commit()
        await db.refresh(submission)
    else:
        await db.flush()
    return submission
