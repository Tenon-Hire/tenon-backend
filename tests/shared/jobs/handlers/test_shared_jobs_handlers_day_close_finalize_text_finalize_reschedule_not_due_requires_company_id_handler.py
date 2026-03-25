from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_reschedule_not_due_requires_company_id(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="finalize-window-company-id@test.com"
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
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

    original_getattr = builtins.getattr

    def _fake_getattr(obj, name, *default):
        if name == "company_id" and obj.__class__.__name__ == "Simulation":
            return None
        return original_getattr(obj, name, *default)

    monkeypatch.setattr(builtins, "getattr", _fake_getattr)

    with pytest.raises(RuntimeError, match="company_id required to reschedule"):
        await finalize_handler.handle_day_close_finalize_text(
            _payload(
                candidate_session_id=candidate_session.id,
                task_id=tasks[0].id,
                day_index=1,
                window_end_at=window_end_by_day[1],
            )
        )
