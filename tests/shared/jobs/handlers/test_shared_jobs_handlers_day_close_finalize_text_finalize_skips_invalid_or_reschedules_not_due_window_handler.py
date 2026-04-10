from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_skips_invalid_or_reschedules_not_due_window(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="finalize-window@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        with_default_schedule=False,
    )
    await async_session.commit()
    window_end_by_day = await _set_fully_closed_schedule(
        async_session,
        candidate_session=candidate_session,
    )

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )

    monkeypatch.setattr(
        finalize_handler.cs_service,
        "compute_task_window",
        lambda *_args, **_kwargs: SimpleNamespace(window_end_at=None),
    )
    invalid_result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=tasks[0].id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )
    assert invalid_result["status"] == "skipped_invalid_window"

    earlier_window_end = datetime.now(UTC) + timedelta(minutes=30)
    existing_job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
        idempotency_key=day_close_finalize_text_idempotency_key(
            candidate_session.id, tasks[0].id
        ),
        payload_json=build_day_close_finalize_text_payload(
            candidate_session_id=candidate_session.id,
            task_id=tasks[0].id,
            day_index=1,
            window_end_at=earlier_window_end,
        ),
        company_id=trial.company_id,
        candidate_session_id=candidate_session.id,
        next_run_at=earlier_window_end,
        commit=True,
    )
    rescheduled_window_end = datetime.now(UTC) + timedelta(hours=2)
    monkeypatch.setattr(
        finalize_handler.cs_service,
        "compute_task_window",
        lambda *_args, **_kwargs: SimpleNamespace(window_end_at=rescheduled_window_end),
    )
    not_due_result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=tasks[0].id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )
    assert not_due_result["status"] == "rescheduled_not_due"

    refreshed_job = await jobs_repo.get_by_id(async_session, existing_job.id)
    assert refreshed_job is not None
    next_run_at = refreshed_job.next_run_at
    assert next_run_at is not None
    if next_run_at.tzinfo is None:
        next_run_at = next_run_at.replace(tzinfo=UTC)
    assert next_run_at == rescheduled_window_end
    assert refreshed_job.payload_json["windowEndAt"] == rescheduled_window_end.replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    submission_count = (
        await async_session.execute(
            select(func.count())
            .select_from(Submission)
            .where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == tasks[0].id,
            )
        )
    ).scalar_one()
    assert submission_count == 0
