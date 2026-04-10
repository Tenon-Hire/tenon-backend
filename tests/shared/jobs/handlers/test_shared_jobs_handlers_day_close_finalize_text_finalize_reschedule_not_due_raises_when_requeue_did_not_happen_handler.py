from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_reschedule_not_due_raises_when_requeue_did_not_happen(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="finalize-window-terminal@test.com"
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
    future_window_end = datetime.now(UTC) + timedelta(hours=2)
    monkeypatch.setattr(
        finalize_handler.cs_service,
        "compute_task_window",
        lambda *_args, **_kwargs: SimpleNamespace(window_end_at=future_window_end),
    )

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
            window_end_at=future_window_end,
        ),
        company_id=trial.company_id,
        candidate_session_id=candidate_session.id,
        next_run_at=future_window_end,
        commit=True,
    )
    existing_job.status = JOB_STATUS_SUCCEEDED
    await async_session.commit()

    with pytest.raises(RuntimeError, match="unable to reschedule idempotent job"):
        await finalize_handler.handle_day_close_finalize_text(
            _payload(
                candidate_session_id=candidate_session.id,
                task_id=tasks[0].id,
                day_index=1,
                window_end_at=window_end_by_day[1],
            )
        )
