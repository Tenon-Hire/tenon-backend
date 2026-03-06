from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import CandidateSession, Job, Task
from app.repositories.jobs import repository as jobs_repo
from app.services.candidate_sessions.schedule_gates import compute_task_window
from app.services.submissions.payload_validation import TEXT_TASK_TYPES

DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE = "day_close_finalize_text"
DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS = 8
DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES = {1, 5}


def day_close_finalize_text_idempotency_key(
    candidate_session_id: int,
    task_id: int,
) -> str:
    return f"day_close_finalize_text:{candidate_session_id}:{task_id}"


def _to_utc_z(value: datetime) -> str:
    normalized = value.astimezone(UTC).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")


def build_day_close_finalize_text_payload(
    *,
    candidate_session_id: int,
    task_id: int,
    day_index: int,
    window_end_at: datetime,
) -> dict[str, object]:
    return {
        "candidateSessionId": candidate_session_id,
        "taskId": task_id,
        "dayIndex": day_index,
        "windowEndAt": _to_utc_z(window_end_at),
    }


async def enqueue_day_close_finalize_text_jobs(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    commit: bool = False,
) -> list[Job]:
    simulation = getattr(candidate_session, "simulation", None)
    if simulation is None:
        return []

    tasks = (
        (
            await db.execute(
                select(Task)
                .where(
                    Task.simulation_id == candidate_session.simulation_id,
                    Task.day_index.in_(DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES),
                )
                .order_by(Task.day_index.asc(), Task.id.asc())
            )
        )
        .scalars()
        .all()
    )

    jobs: list[Job] = []
    for task in tasks:
        if (task.type or "").strip().lower() not in TEXT_TASK_TYPES:
            continue

        task_window = compute_task_window(candidate_session, task)
        if task_window.window_end_at is None:
            continue

        payload = build_day_close_finalize_text_payload(
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            day_index=task.day_index,
            window_end_at=task_window.window_end_at,
        )
        job = await jobs_repo.create_or_update_idempotent(
            db,
            job_type=DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
            idempotency_key=day_close_finalize_text_idempotency_key(
                candidate_session.id, task.id
            ),
            payload_json=payload,
            company_id=simulation.company_id,
            candidate_session_id=candidate_session.id,
            max_attempts=DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS,
            correlation_id=f"candidate_session:{candidate_session.id}:schedule",
            next_run_at=task_window.window_end_at,
            commit=False,
        )
        jobs.append(job)

    if commit:
        await db.commit()

    return jobs


__all__ = [
    "DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE",
    "DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS",
    "DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES",
    "build_day_close_finalize_text_payload",
    "day_close_finalize_text_idempotency_key",
    "enqueue_day_close_finalize_text_jobs",
]
