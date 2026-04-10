from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_enqueue_service as enqueue_service,
)


class _FakeDB:
    def __init__(self) -> None:
        self.commit_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1


@pytest.mark.asyncio
async def test_enqueue_day_close_finalize_text_jobs_impl_commit_false_skips_db_commit():
    db = _FakeDB()
    candidate_session = SimpleNamespace(
        id=1,
        trial=SimpleNamespace(company_id=11),
        trial_id=99,
    )
    task = SimpleNamespace(id=101, day_index=1, type="documentation")

    async def _load_tasks_for_day_indexes(*_args, **_kwargs):
        return [task]

    def _compute_task_window(_candidate_session, _task):
        return SimpleNamespace(window_end_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC))

    async def _upsert_day_close_jobs(*_args, **_kwargs):
        return ["finalize-job"]

    def _finalize_text_job_spec(**kwargs):
        return kwargs

    jobs = await enqueue_service.enqueue_day_close_finalize_text_jobs_impl(
        db=db,
        candidate_session=candidate_session,
        load_tasks_for_day_indexes=_load_tasks_for_day_indexes,
        compute_task_window=_compute_task_window,
        upsert_day_close_jobs=_upsert_day_close_jobs,
        finalize_text_job_spec=_finalize_text_job_spec,
        commit=False,
    )

    assert jobs == ["finalize-job"]
    assert db.commit_calls == 0


@pytest.mark.asyncio
async def test_enqueue_day_close_enforcement_jobs_impl_commit_false_skips_db_commit():
    db = _FakeDB()
    candidate_session = SimpleNamespace(
        id=2,
        trial=SimpleNamespace(company_id=12),
        trial_id=100,
    )
    task = SimpleNamespace(id=202, day_index=2, type="code")

    async def _load_tasks_for_day_indexes(*_args, **_kwargs):
        return [task]

    def _compute_task_window(_candidate_session, _task):
        return SimpleNamespace(window_end_at=datetime(2026, 3, 21, 12, 0, tzinfo=UTC))

    async def _upsert_day_close_jobs(*_args, **_kwargs):
        return ["enforcement-job"]

    def _enforcement_job_spec(**kwargs):
        return kwargs

    jobs = await enqueue_service.enqueue_day_close_enforcement_jobs_impl(
        db=db,
        candidate_session=candidate_session,
        load_tasks_for_day_indexes=_load_tasks_for_day_indexes,
        compute_task_window=_compute_task_window,
        upsert_day_close_jobs=_upsert_day_close_jobs,
        enforcement_job_spec=_enforcement_job_spec,
        commit=False,
    )

    assert jobs == ["enforcement-job"]
    assert db.commit_calls == 0


@pytest.mark.asyncio
async def test_enqueue_day_close_jobs_impl_returns_empty_tuples_without_trial():
    result = await enqueue_service.enqueue_day_close_jobs_impl(
        db=_FakeDB(),
        candidate_session=SimpleNamespace(trial=None),
        load_tasks_for_day_indexes=lambda *_args, **_kwargs: None,
        compute_task_window=lambda *_args, **_kwargs: None,
        upsert_day_close_jobs=lambda *_args, **_kwargs: None,
        finalize_text_job_spec=lambda **_kwargs: None,
        enforcement_job_spec=lambda **_kwargs: None,
        commit=False,
    )

    assert result == ([], [])


@pytest.mark.asyncio
async def test_enqueue_day_close_jobs_impl_skips_missing_window_and_commits_when_requested():
    db = _FakeDB()
    candidate_session = SimpleNamespace(
        id=3,
        trial=SimpleNamespace(company_id=13),
        trial_id=101,
    )
    finalize_task = SimpleNamespace(id=301, day_index=1, type="documentation")
    skipped_task = SimpleNamespace(id=302, day_index=5, type="documentation")
    enforcement_task = SimpleNamespace(id=303, day_index=2, type="code")

    async def _load_tasks_for_day_indexes(*_args, **_kwargs):
        return [finalize_task, skipped_task, enforcement_task]

    def _compute_task_window(_candidate_session, task):
        if task.id == 302:
            return SimpleNamespace(window_end_at=None)
        return SimpleNamespace(window_end_at=datetime(2026, 3, 22, 12, 0, tzinfo=UTC))

    async def _upsert_day_close_jobs(*_args, specs, **_kwargs):
        return list(specs)

    def _finalize_text_job_spec(**kwargs):
        return {"kind": "finalize", **kwargs}

    def _enforcement_job_spec(**kwargs):
        return {"kind": "enforcement", **kwargs}

    finalize_jobs, enforcement_jobs = await enqueue_service.enqueue_day_close_jobs_impl(
        db=db,
        candidate_session=candidate_session,
        load_tasks_for_day_indexes=_load_tasks_for_day_indexes,
        compute_task_window=_compute_task_window,
        upsert_day_close_jobs=_upsert_day_close_jobs,
        finalize_text_job_spec=_finalize_text_job_spec,
        enforcement_job_spec=_enforcement_job_spec,
        commit=True,
    )

    assert len(finalize_jobs) == 1
    assert len(enforcement_jobs) == 1
    assert finalize_jobs[0]["task_id"] == 301
    assert enforcement_jobs[0]["task_id"] == 303
    assert db.commit_calls == 1
