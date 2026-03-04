from __future__ import annotations

import asyncio
import inspect
import logging
import os
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import async_session_maker
from app.repositories.jobs import repository as jobs_repo

logger = logging.getLogger(__name__)

DEFAULT_LEASE_SECONDS = 300
DEFAULT_BASE_BACKOFF_SECONDS = 1
DEFAULT_MAX_BACKOFF_SECONDS = 60
DEFAULT_IDLE_SLEEP_SECONDS = 1.0

JobHandler = Callable[
    [dict[str, Any]],
    Awaitable[dict[str, Any] | None] | dict[str, Any] | None,
]
_HANDLERS: dict[str, JobHandler] = {}


class RetryableJobError(Exception):
    """Signals a transient handler failure that should be retried."""


class PermanentJobError(Exception):
    """Signals an unrecoverable handler failure."""


def register_handler(job_type: str, handler: JobHandler) -> None:
    normalized = job_type.strip()
    if not normalized:
        raise ValueError("job_type is required")
    _HANDLERS[normalized] = handler


def clear_handlers() -> None:
    _HANDLERS.clear()


def has_handler(job_type: str) -> bool:
    normalized = job_type.strip()
    if not normalized:
        return False
    return normalized in _HANDLERS


def register_builtin_handlers() -> None:
    from app.jobs.handlers import (
        SIMULATION_CLEANUP_JOB_TYPE,
        handle_simulation_cleanup,
    )

    register_handler(SIMULATION_CLEANUP_JOB_TYPE, handle_simulation_cleanup)


def compute_backoff_seconds(
    attempt: int,
    *,
    base_seconds: int = DEFAULT_BASE_BACKOFF_SECONDS,
    max_seconds: int = DEFAULT_MAX_BACKOFF_SECONDS,
) -> int:
    if attempt < 1:
        return base_seconds
    return min(max_seconds, base_seconds * (2 ** (attempt - 1)))


def _build_worker_id() -> str:
    pid = os.getpid()
    host = socket.gethostname()
    return f"{host}:{pid}"


def _format_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


async def _invoke_handler(
    handler: JobHandler,
    payload_json: dict[str, Any],
) -> dict[str, Any] | None:
    value = handler(payload_json)
    if inspect.isawaitable(value):
        value = await value
    if value is not None and not isinstance(value, dict):
        raise PermanentJobError("job handler result must be a JSON object or null")
    return value


async def run_once(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    worker_id: str | None = None,
    now: datetime | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    base_backoff_seconds: int = DEFAULT_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: int = DEFAULT_MAX_BACKOFF_SECONDS,
) -> bool:
    """Claim and process one runnable job. Returns True when a job was handled."""
    claim_time = now or datetime.now(UTC)
    resolved_worker_id = worker_id or _build_worker_id()

    async with session_maker() as db:
        job = await jobs_repo.claim_next_runnable(
            db,
            worker_id=resolved_worker_id,
            now=claim_time,
            lease_seconds=lease_seconds,
        )
    if job is None:
        return False

    log_extra = {
        "jobId": job.id,
        "jobType": job.job_type,
        "attempt": job.attempt,
        "correlation_id": job.correlation_id,
    }
    logger.info("job_claimed", extra=log_extra)

    handler = _HANDLERS.get(job.job_type)
    if handler is None:
        error = f"PermanentJobError: no handler registered for job_type={job.job_type}"
        async with session_maker() as db:
            await jobs_repo.mark_dead_letter(
                db, job_id=job.id, error_str=error, now=claim_time
            )
        logger.warning("job_dead_letter", extra=log_extra)
        return True

    try:
        result = await _invoke_handler(handler, job.payload_json or {})
    except PermanentJobError as exc:
        async with session_maker() as db:
            await jobs_repo.mark_dead_letter(
                db, job_id=job.id, error_str=_format_error(exc), now=claim_time
            )
        logger.warning("job_dead_letter", extra=log_extra)
        return True
    except Exception as exc:
        error = _format_error(exc)
        if job.attempt < job.max_attempts:
            delay_seconds = compute_backoff_seconds(
                job.attempt,
                base_seconds=base_backoff_seconds,
                max_seconds=max_backoff_seconds,
            )
            next_run_at = claim_time + timedelta(seconds=delay_seconds)
            async with session_maker() as db:
                await jobs_repo.mark_failed_and_reschedule(
                    db,
                    job_id=job.id,
                    error_str=error,
                    next_run_at=next_run_at,
                    now=claim_time,
                )
            logger.info(
                "job_rescheduled",
                extra={
                    **log_extra,
                    "delay_seconds": delay_seconds,
                    "next_run_at": next_run_at.isoformat(),
                },
            )
            return True

        async with session_maker() as db:
            await jobs_repo.mark_dead_letter(
                db, job_id=job.id, error_str=error, now=claim_time
            )
        logger.warning("job_dead_letter", extra=log_extra)
        return True

    async with session_maker() as db:
        await jobs_repo.mark_succeeded(
            db,
            job_id=job.id,
            result_json=result,
            now=claim_time,
        )
    logger.info("job_succeeded", extra=log_extra)
    return True


async def run_forever(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    worker_id: str | None = None,
    idle_sleep_seconds: float = DEFAULT_IDLE_SLEEP_SECONDS,
) -> None:  # pragma: no cover - exercised manually via CLI
    resolved_worker_id = worker_id or _build_worker_id()
    logger.info("jobs_worker_started", extra={"worker_id": resolved_worker_id})
    while True:
        handled = await run_once(
            session_maker=session_maker, worker_id=resolved_worker_id
        )
        if not handled:
            await asyncio.sleep(idle_sleep_seconds)


def main() -> None:  # pragma: no cover - thin CLI wrapper
    register_builtin_handlers()
    asyncio.run(run_forever())


if __name__ == "__main__":  # pragma: no cover - module entrypoint
    main()
