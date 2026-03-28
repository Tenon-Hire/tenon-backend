from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.shared.jobs import shared_jobs_worker_service as worker_service
from app.shared.jobs import worker
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_SUCCEEDED,
)
from tests.shared.jobs.shared_jobs_worker_utils import _session_maker, create_job


@pytest.mark.asyncio
async def test_compute_backoff_seconds():
    assert worker.compute_backoff_seconds(0) == 1
    assert worker.compute_backoff_seconds(1) == 1
    assert worker.compute_backoff_seconds(2) == 2
    assert worker.compute_backoff_seconds(3) == 4
    assert worker.compute_backoff_seconds(20) == 60


@pytest.mark.asyncio
async def test_run_once_returns_false_when_no_jobs(async_session):
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-empty",
        now=datetime.now(UTC),
    )
    assert handled is False


@pytest.mark.asyncio
async def test_run_once_succeeds_and_marks_result(async_session):
    job = await create_job(
        async_session,
        job_type="worker_success",
        idempotency_key="worker-success-1",
        payload_json={"x": 1},
    )

    async def _handler(payload):
        assert payload == {"x": 1}
        return {"ok": True}

    worker.register_handler("worker_success", _handler)
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-success",
        now=datetime.now(UTC),
    )
    assert handled is True

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_SUCCEEDED
    assert refreshed.attempt == 1
    assert refreshed.result_json == {"ok": True}
    assert refreshed.last_error is None


def test_build_worker_id_uses_hostname_and_pid(monkeypatch):
    monkeypatch.setattr(worker_service.socket, "gethostname", lambda: "unit-host")
    monkeypatch.setattr(worker_service.os, "getpid", lambda: 4321)

    assert worker_service._build_worker_id() == "unit-host:4321"
