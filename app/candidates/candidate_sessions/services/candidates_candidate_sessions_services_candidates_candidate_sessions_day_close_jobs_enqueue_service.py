"""Application module for candidates candidate sessions services candidates candidate sessions day close jobs enqueue service workflows."""

from __future__ import annotations

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_constants import (
    DAY_CLOSE_ALL_DAY_INDEXES,
    DAY_CLOSE_ENFORCEMENT_DAY_INDEXES,
    DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.submissions.services.submissions_services_submissions_payload_validation_service import (
    CODE_TASK_TYPES,
    TEXT_TASK_TYPES,
)


async def enqueue_day_close_finalize_text_jobs_impl(
    *,
    db,
    candidate_session,
    load_tasks_for_day_indexes,
    compute_task_window,
    upsert_day_close_jobs,
    finalize_text_job_spec,
    commit: bool = False,
):
    """Enqueue day close finalize text jobs impl."""
    simulation = getattr(candidate_session, "simulation", None)
    if simulation is None:
        return []
    tasks = await load_tasks_for_day_indexes(
        db,
        simulation_id=candidate_session.simulation_id,
        day_indexes=DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES,
    )
    specs: list[jobs_repo.IdempotentJobSpec] = []
    for task in tasks:
        if (task.type or "").strip().lower() not in TEXT_TASK_TYPES:
            continue
        task_window = compute_task_window(candidate_session, task)
        if task_window.window_end_at is None:
            continue
        specs.append(
            finalize_text_job_spec(
                candidate_session_id=candidate_session.id,
                task_id=task.id,
                day_index=task.day_index,
                window_end_at=task_window.window_end_at,
            )
        )
    jobs = await upsert_day_close_jobs(
        db, company_id=simulation.company_id, specs=specs
    )
    if commit:
        await db.commit()
    return jobs


async def enqueue_day_close_enforcement_jobs_impl(
    *,
    db,
    candidate_session,
    load_tasks_for_day_indexes,
    compute_task_window,
    upsert_day_close_jobs,
    enforcement_job_spec,
    commit: bool = False,
):
    """Enqueue day close enforcement jobs impl."""
    simulation = getattr(candidate_session, "simulation", None)
    if simulation is None:
        return []
    tasks = await load_tasks_for_day_indexes(
        db,
        simulation_id=candidate_session.simulation_id,
        day_indexes=DAY_CLOSE_ENFORCEMENT_DAY_INDEXES,
    )
    specs: list[jobs_repo.IdempotentJobSpec] = []
    for task in tasks:
        if (task.type or "").strip().lower() not in CODE_TASK_TYPES:
            continue
        task_window = compute_task_window(candidate_session, task)
        if task_window.window_end_at is None:
            continue
        specs.append(
            enforcement_job_spec(
                candidate_session_id=candidate_session.id,
                task_id=task.id,
                day_index=task.day_index,
                window_end_at=task_window.window_end_at,
            )
        )
    jobs = await upsert_day_close_jobs(
        db, company_id=simulation.company_id, specs=specs
    )
    if commit:
        await db.commit()
    return jobs


async def enqueue_day_close_jobs_impl(
    *,
    db,
    candidate_session,
    load_tasks_for_day_indexes,
    compute_task_window,
    upsert_day_close_jobs,
    finalize_text_job_spec,
    enforcement_job_spec,
    commit: bool = False,
):
    """Enqueue day close jobs impl."""
    simulation = getattr(candidate_session, "simulation", None)
    if simulation is None:
        return [], []
    tasks = await load_tasks_for_day_indexes(
        db,
        simulation_id=candidate_session.simulation_id,
        day_indexes=DAY_CLOSE_ALL_DAY_INDEXES,
    )
    finalize_specs: list[jobs_repo.IdempotentJobSpec] = []
    enforcement_specs: list[jobs_repo.IdempotentJobSpec] = []
    for task in tasks:
        task_type = (task.type or "").strip().lower()
        task_window = compute_task_window(candidate_session, task)
        if task_window.window_end_at is None:
            continue
        if (
            task.day_index in DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES
            and task_type in TEXT_TASK_TYPES
        ):
            finalize_specs.append(
                finalize_text_job_spec(
                    candidate_session_id=candidate_session.id,
                    task_id=task.id,
                    day_index=task.day_index,
                    window_end_at=task_window.window_end_at,
                )
            )
        if (
            task.day_index in DAY_CLOSE_ENFORCEMENT_DAY_INDEXES
            and task_type in CODE_TASK_TYPES
        ):
            enforcement_specs.append(
                enforcement_job_spec(
                    candidate_session_id=candidate_session.id,
                    task_id=task.id,
                    day_index=task.day_index,
                    window_end_at=task_window.window_end_at,
                )
            )
    finalize_jobs = await upsert_day_close_jobs(
        db, company_id=simulation.company_id, specs=finalize_specs
    )
    enforcement_jobs = await upsert_day_close_jobs(
        db, company_id=simulation.company_id, specs=enforcement_specs
    )
    if commit:
        await db.commit()
    return finalize_jobs, enforcement_jobs


__all__ = [
    "enqueue_day_close_enforcement_jobs_impl",
    "enqueue_day_close_finalize_text_jobs_impl",
    "enqueue_day_close_jobs_impl",
]
