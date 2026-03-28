"""Application module for jobs worker runtime reschedule paths service workflows."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_failure_paths_service import (
    retry_or_dead_letter,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_state_writes_service import (
    get_job_by_id,
)


async def _verify_handler_rescheduled(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    job_id: str,
) -> bool:
    refreshed = await get_job_by_id(session_maker, job_id=job_id)
    if refreshed is None:
        return False
    return (
        refreshed.status == JOB_STATUS_QUEUED
        and not refreshed.locked_at
        and not refreshed.locked_by
    )


async def handle_handler_reschedule(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    job: Any,
    result: dict[str, Any] | None,
    claim_time: datetime,
    log_extra: dict[str, Any],
    base_backoff_seconds: int,
    max_backoff_seconds: int,
    logger: logging.Logger,
) -> bool:
    """Handle handler reschedule."""
    if result is None or result.get("_jobDisposition") != "rescheduled":
        return False
    if await _verify_handler_rescheduled(session_maker, job_id=job.id):
        logger.info("job_rescheduled_by_handler", extra=log_extra)
        return True
    error = "handler_reschedule_failed: job still running/locked after handler disposition=rescheduled"
    await retry_or_dead_letter(
        session_maker,
        job=job,
        error_str=error,
        claim_time=claim_time,
        log_extra=log_extra,
        base_backoff_seconds=base_backoff_seconds,
        max_backoff_seconds=max_backoff_seconds,
        logger=logger,
        warn_event="job_reschedule_verification_failed",
        log_as_warning=True,
    )
    return True


__all__ = ["handle_handler_reschedule"]
