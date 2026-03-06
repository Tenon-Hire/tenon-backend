from __future__ import annotations

import builtins
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains import Submission
from app.jobs.handlers import day_close_finalize_text as finalize_handler
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import JOB_STATUS_SUCCEEDED
from app.repositories.task_drafts import repository as task_drafts_repo
from app.services.candidate_sessions.day_close_jobs import (
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
    build_day_close_finalize_text_payload,
    day_close_finalize_text_idempotency_key,
)
from app.services.scheduling.day_windows import serialize_day_windows
from app.services.task_drafts import NO_DRAFT_AT_CUTOFF_MARKER
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
    create_submission,
)


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )


async def _set_fully_closed_schedule(
    async_session, *, candidate_session
) -> dict[int, datetime]:
    now_utc = datetime.now(UTC).replace(microsecond=0)
    day_windows: list[dict[str, object]] = []
    window_end_by_day: dict[int, datetime] = {}
    for day_index in range(1, 6):
        window_end = now_utc - timedelta(days=6 - day_index)
        window_start = window_end - timedelta(hours=8)
        day_windows.append(
            {
                "dayIndex": day_index,
                "windowStartAt": window_start,
                "windowEndAt": window_end,
            }
        )
        window_end_by_day[day_index] = window_end

    candidate_session.scheduled_start_at = day_windows[0]["windowStartAt"]
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()
    return window_end_by_day


def _payload(
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
        "windowEndAt": window_end_at.isoformat().replace("+00:00", "Z"),
    }


@pytest.mark.asyncio
async def test_finalize_from_draft_creates_submission_and_marks_draft(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(async_session, email="finalize-draft@test.com")
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

    day1_task = tasks[0]
    draft = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="## Day 1 draft",
        content_json={"reflection": {"decisions": "use queue"}},
    )
    assert draft.finalized_submission_id is None

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )

    result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=day1_task.id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )

    assert result["status"] == "created_submission"
    assert result["source"] == "draft"

    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == day1_task.id,
            )
        )
    ).scalar_one()
    assert submission.content_text == "## Day 1 draft"
    assert submission.content_json == {"reflection": {"decisions": "use queue"}}

    finalized_draft = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
    )
    assert finalized_draft is not None
    assert finalized_draft.finalized_submission_id == submission.id
    assert finalized_draft.finalized_at is not None


@pytest.mark.asyncio
async def test_finalize_no_draft_creates_empty_marker_submission(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(async_session, email="finalize-empty@test.com")
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
    day5_task = tasks[4]

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=day5_task.id,
            day_index=5,
            window_end_at=window_end_by_day[5],
        )
    )

    assert result["status"] == "created_submission"
    assert result["source"] == "no_draft_marker"

    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == day5_task.id,
            )
        )
    ).scalar_one()
    assert submission.content_text == ""
    assert submission.content_json == NO_DRAFT_AT_CUTOFF_MARKER


@pytest.mark.asyncio
async def test_finalize_is_idempotent_when_run_twice(async_session, monkeypatch):
    recruiter = await create_recruiter(
        async_session, email="finalize-idempotent@test.com"
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
    day1_task = tasks[0]

    await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="idempotent draft",
        content_json={"v": 1},
    )

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    first = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=day1_task.id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )
    second = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=day1_task.id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )

    assert first["status"] == "created_submission"
    assert second["status"] == "no_op_existing_submission"

    submission_count = (
        await async_session.execute(
            select(func.count())
            .select_from(Submission)
            .where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == day1_task.id,
            )
        )
    ).scalar_one()
    assert submission_count == 1


@pytest.mark.asyncio
async def test_finalize_manual_submit_precedence_is_noop(async_session, monkeypatch):
    recruiter = await create_recruiter(async_session, email="finalize-manual@test.com")
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
    day1_task = tasks[0]

    manual_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=day1_task,
        content_text="manual submit",
        content_json={"manual": True},
    )
    await async_session.commit()

    await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="late draft",
        content_json={"draft": True},
    )

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=day1_task.id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )

    assert result["status"] == "no_op_existing_submission"
    assert result["submissionId"] == manual_submission.id

    same_submission = (
        await async_session.execute(
            select(Submission).where(Submission.id == manual_submission.id)
        )
    ).scalar_one()
    assert same_submission.content_text == "manual submit"
    assert same_submission.content_json == {"manual": True}

    draft = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
    )
    assert draft is not None
    assert draft.finalized_submission_id == manual_submission.id


def test_parse_helpers_cover_edge_cases() -> None:
    assert finalize_handler._parse_positive_int(True) is None
    assert finalize_handler._parse_positive_int("12") == 12
    assert finalize_handler._parse_positive_int("0") is None
    assert finalize_handler._parse_positive_int("12x") is None
    assert finalize_handler._parse_positive_int(-1) is None

    assert finalize_handler._parse_optional_datetime(123) is None
    assert finalize_handler._parse_optional_datetime("") is None
    assert finalize_handler._parse_optional_datetime("bad-iso") is None
    naive = finalize_handler._parse_optional_datetime("2026-03-10T18:30:00")
    assert naive is not None
    assert naive.tzinfo == UTC


@pytest.mark.asyncio
async def test_finalize_skips_invalid_payload():
    result = await finalize_handler.handle_day_close_finalize_text(
        {"candidateSessionId": "abc", "taskId": 0}
    )
    assert result["status"] == "skipped_invalid_payload"


@pytest.mark.asyncio
async def test_finalize_session_not_found(async_session, monkeypatch):
    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    result = await finalize_handler.handle_day_close_finalize_text(
        {
            "candidateSessionId": 999999,
            "taskId": 123,
            "dayIndex": 1,
            "windowEndAt": "2026-03-10T18:30:00Z",
        }
    )
    assert result["status"] == "candidate_session_not_found"


@pytest.mark.asyncio
async def test_finalize_task_not_found(async_session, monkeypatch):
    recruiter = await create_recruiter(async_session, email="finalize-task404@test.com")
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=False,
    )
    await async_session.commit()

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    result = await finalize_handler.handle_day_close_finalize_text(
        {
            "candidateSessionId": candidate_session.id,
            "taskId": 999999,
            "dayIndex": 1,
            "windowEndAt": "2026-03-10T18:30:00Z",
        }
    )
    assert result["status"] == "task_not_found"


@pytest.mark.asyncio
async def test_finalize_skips_non_text_task(async_session, monkeypatch):
    recruiter = await create_recruiter(async_session, email="finalize-nontext@test.com")
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=False,
    )
    tasks[0].type = "code"
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
    result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=tasks[0].id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )
    assert result["status"] == "skipped_non_text_task"


@pytest.mark.asyncio
async def test_finalize_skips_invalid_or_reschedules_not_due_window(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(async_session, email="finalize-window@test.com")
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
        company_id=simulation.company_id,
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


@pytest.mark.asyncio
async def test_finalize_reschedule_not_due_raises_when_requeue_did_not_happen(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="finalize-window-terminal@test.com"
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
        company_id=simulation.company_id,
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


@pytest.mark.asyncio
async def test_finalize_conflict_branch_marks_draft_with_existing_submission(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="finalize-conflict@test.com"
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
    day1_task = tasks[0]

    existing_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=day1_task,
        content_text="manual",
    )
    await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="draft",
        content_json={"k": "v"},
    )

    call_count = {"n": 0}

    async def _fake_get_existing(*_args, **_kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None
        return existing_submission

    async def _raise_conflict(*_args, **_kwargs):
        raise finalize_handler.SubmissionConflict()

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    monkeypatch.setattr(
        finalize_handler, "_get_existing_submission", _fake_get_existing
    )
    monkeypatch.setattr(
        finalize_handler.submission_service,
        "create_submission",
        _raise_conflict,
    )

    result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=day1_task.id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )

    assert result["status"] == "no_op_existing_submission"
    assert result["submissionId"] == existing_submission.id
    assert result["source"] == "draft"
    draft = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
    )
    assert draft is not None
    assert draft.finalized_submission_id == existing_submission.id


@pytest.mark.asyncio
async def test_finalize_conflict_without_existing_submission_reraises(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="finalize-conflict-raise@test.com"
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

    day1_task = tasks[0]
    await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="draft",
        content_json={"k": "v"},
    )

    async def _none_existing(*_args, **_kwargs):
        return None

    async def _raise_conflict(*_args, **_kwargs):
        raise finalize_handler.SubmissionConflict()

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    monkeypatch.setattr(finalize_handler, "_get_existing_submission", _none_existing)
    monkeypatch.setattr(
        finalize_handler.submission_service,
        "create_submission",
        _raise_conflict,
    )

    with pytest.raises(finalize_handler.SubmissionConflict):
        await finalize_handler.handle_day_close_finalize_text(
            _payload(
                candidate_session_id=candidate_session.id,
                task_id=day1_task.id,
                day_index=1,
                window_end_at=window_end_by_day[1],
            )
        )
