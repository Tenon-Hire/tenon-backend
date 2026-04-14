from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.shared.jobs.worker_runtime import (
    shared_jobs_worker_runtime_failure_paths_service as failure_paths,
)


@pytest.mark.asyncio
async def test_retry_or_dead_letter_uses_provider_backoff_for_rate_limit_errors(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}
    claim_time = datetime(2026, 4, 3, tzinfo=UTC)

    async def _mark_failed_and_reschedule(
        _session_maker,
        *,
        job_id,
        error_str,
        next_run_at,
        claim_time,
    ):
        observed["job_id"] = job_id
        observed["error_str"] = error_str
        observed["next_run_at"] = next_run_at
        observed["claim_time"] = claim_time

    monkeypatch.setattr(
        failure_paths,
        "mark_failed_and_reschedule",
        _mark_failed_and_reschedule,
    )

    logger = SimpleNamespace(
        info=lambda *_args, **_kwargs: None,
        warning=lambda *_args, **_kwargs: None,
    )
    job = SimpleNamespace(id="job-1", attempt=1, max_attempts=7)

    await failure_paths.retry_or_dead_letter(
        object(),
        job=job,
        error_str="RuntimeError: openai_request_failed:RateLimitError",
        claim_time=claim_time,
        log_extra={},
        base_backoff_seconds=1,
        max_backoff_seconds=60,
        logger=logger,
        warn_event="job_rescheduled",
    )

    assert observed["job_id"] == "job-1"
    assert observed["next_run_at"] == claim_time + timedelta(seconds=15)


def test_is_provider_backoff_error_returns_false_for_blank_string():
    assert failure_paths._is_provider_backoff_error("   ") is False


@pytest.mark.asyncio
async def test_retry_or_dead_letter_dead_letters_when_attempt_budget_exhausted(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}
    claim_time = datetime(2026, 4, 3, tzinfo=UTC)

    async def _mark_dead_letter(_session_maker, *, job_id, error_str, claim_time):
        observed["job_id"] = job_id
        observed["error_str"] = error_str
        observed["claim_time"] = claim_time

    monkeypatch.setattr(failure_paths, "mark_dead_letter", _mark_dead_letter)

    logger = SimpleNamespace(
        info=lambda *_args, **_kwargs: None,
        warning=lambda *_args, **_kwargs: None,
    )
    job = SimpleNamespace(id="job-2", attempt=7, max_attempts=7)

    await failure_paths.retry_or_dead_letter(
        object(),
        job=job,
        error_str="RuntimeError: terminal failure",
        claim_time=claim_time,
        log_extra={},
        base_backoff_seconds=1,
        max_backoff_seconds=60,
        logger=logger,
        warn_event="job_rescheduled",
    )

    assert observed["job_id"] == "job-2"
