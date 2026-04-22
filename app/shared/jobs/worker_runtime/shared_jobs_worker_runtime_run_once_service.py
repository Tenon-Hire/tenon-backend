"""Application module for jobs worker runtime run once service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.database import async_session_maker
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_failure_paths_service import (
    handle_handler_exception,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_invocation_service import (
    invoke_handler,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_log_context_service import (
    build_log_extra,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_missing_handler import (
    dead_letter_missing_handler,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_registry_service import (
    get_handler,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_reschedule_paths_service import (
    handle_handler_reschedule,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_state_writes_service import (
    mark_succeeded,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_types_model import (
    DEFAULT_BASE_BACKOFF_SECONDS,
    DEFAULT_LEASE_SECONDS,
    DEFAULT_MAX_BACKOFF_SECONDS,
)

logger = logging.getLogger(__name__)


async def run_once(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    base_backoff_seconds: int = DEFAULT_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: int = DEFAULT_MAX_BACKOFF_SECONDS,
) -> bool:
    """Run once."""
    claim_time = now or datetime.now(UTC)
    async with session_maker() as db:
        job = await jobs_repo.claim_next_runnable(
            db,
            worker_id=worker_id,
            now=claim_time,
            lease_seconds=lease_seconds,
        )
    if job is None:
        return False

    log_extra = build_log_extra(job)
    logger.info("job_claimed", extra=log_extra)
    handler = get_handler(job.job_type)
    if handler is None:
        await dead_letter_missing_handler(
            session_maker,
            job_id=job.id,
            job_type=job.job_type,
            claim_time=claim_time,
        )
        logger.warning("job_dead_letter", extra=log_extra)
        return True

    try:
        handler_payload = dict(job.payload_json or {})
        handler_payload.setdefault("jobId", job.id)
        result = await invoke_handler(handler, handler_payload)
    except Exception as exc:  # pragma: no cover
        await handle_handler_exception(
            session_maker,
            job=job,
            error=exc,
            claim_time=claim_time,
            log_extra=log_extra,
            base_backoff_seconds=base_backoff_seconds,
            max_backoff_seconds=max_backoff_seconds,
            logger=logger,
        )
        return True

    if await handle_handler_reschedule(
        session_maker,
        job=job,
        result=result,
        claim_time=claim_time,
        log_extra=log_extra,
        base_backoff_seconds=base_backoff_seconds,
        max_backoff_seconds=max_backoff_seconds,
        logger=logger,
    ):
        return True

    await mark_succeeded(
        session_maker, job_id=job.id, result=result, claim_time=claim_time
    )
    logger.info("job_succeeded", extra=log_extra)
    return True
