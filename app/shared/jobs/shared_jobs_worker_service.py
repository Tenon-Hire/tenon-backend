"""Application module for jobs worker service workflows."""

from __future__ import annotations

import asyncio
import logging
import os
import socket

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.database import async_session_maker
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_registry_service import (
    clear_handlers,
    has_handler,
    register_builtin_handlers,
    register_handler,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_run_once_service import (
    run_once as _run_once,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_types_model import (
    DEFAULT_IDLE_SLEEP_SECONDS,
    PermanentJobError,
    compute_backoff_seconds,
)

logger = logging.getLogger(__name__)


def _build_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


async def run_once(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    worker_id: str | None = None,
    **kwargs,
) -> bool:
    """Run once."""
    return await _run_once(
        session_maker=session_maker,
        worker_id=worker_id or _build_worker_id(),
        **kwargs,
    )


async def run_forever(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    worker_id: str | None = None,
    idle_sleep_seconds: float = DEFAULT_IDLE_SLEEP_SECONDS,
) -> None:  # pragma: no cover - exercised manually via CLI
    """Run forever."""
    resolved_worker_id = worker_id or _build_worker_id()
    logger.info("jobs_worker_started", extra={"worker_id": resolved_worker_id})
    while True:
        handled = await _run_once(
            session_maker=session_maker, worker_id=resolved_worker_id
        )
        if not handled:
            await asyncio.sleep(idle_sleep_seconds)


def main() -> None:  # pragma: no cover - thin CLI wrapper
    """Execute main."""
    register_builtin_handlers()
    asyncio.run(run_forever())


__all__ = [
    "PermanentJobError",
    "clear_handlers",
    "compute_backoff_seconds",
    "has_handler",
    "main",
    "register_builtin_handlers",
    "register_handler",
    "run_forever",
    "run_once",
]


if __name__ == "__main__":  # pragma: no cover - module entrypoint
    main()
