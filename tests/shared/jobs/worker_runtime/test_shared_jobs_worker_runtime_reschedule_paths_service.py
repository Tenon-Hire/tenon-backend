from __future__ import annotations

import pytest

from app.shared.jobs.worker_runtime import (
    shared_jobs_worker_runtime_reschedule_paths_service as reschedule_paths,
)


@pytest.mark.asyncio
async def test_verify_handler_rescheduled_returns_false_when_job_is_missing(
    monkeypatch,
) -> None:
    async def _fake_get_job_by_id(*_args, **_kwargs):
        return None

    monkeypatch.setattr(reschedule_paths, "get_job_by_id", _fake_get_job_by_id)

    assert (
        await reschedule_paths._verify_handler_rescheduled(object(), job_id="job-1")
        is False
    )
