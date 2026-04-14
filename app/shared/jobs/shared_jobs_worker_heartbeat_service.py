"""Application module for worker heartbeat service workflows."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.shared.database import async_session_maker
from app.shared.jobs import shared_jobs_worker_service as worker_service
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_worker_heartbeats_repository_model import (
    WORKER_HEARTBEAT_STATUS_STOPPED,
)

logger = logging.getLogger(__name__)

DEFAULT_WORKER_SERVICE_NAME = "winoe-worker"


def _build_worker_instance_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def is_worker_heartbeat_fresh(
    heartbeat: object,
    *,
    now: datetime | None = None,
    stale_after_seconds: int | None = None,
) -> bool:
    """Return whether a worker heartbeat is fresh enough for readiness checks."""
    observed_now = now or datetime.now(UTC)
    observed_stale_after_seconds = (
        stale_after_seconds
        if stale_after_seconds is not None
        else settings.WORKER_HEARTBEAT_STALE_SECONDS
    )
    last_heartbeat_at = getattr(heartbeat, "last_heartbeat_at", None)
    if last_heartbeat_at is None:
        return False
    if last_heartbeat_at.tzinfo is None:
        last_heartbeat_at = last_heartbeat_at.replace(tzinfo=UTC)
    return last_heartbeat_at >= observed_now - timedelta(
        seconds=max(1, observed_stale_after_seconds)
    )


async def _write_heartbeat(
    *,
    session_maker: async_sessionmaker[AsyncSession],
    service_name: str,
    instance_id: str,
    now: datetime,
    running: bool,
) -> None:
    async with session_maker() as db:
        if running:
            await jobs_repo.upsert_worker_heartbeat(
                db,
                service_name=service_name,
                instance_id=instance_id,
                now=now,
            )
            return
        await jobs_repo.mark_worker_stopped(
            db,
            service_name=service_name,
            instance_id=instance_id,
            now=now,
        )


async def _heartbeat_loop(
    *,
    session_maker: async_sessionmaker[AsyncSession],
    service_name: str,
    instance_id: str,
    started_at: datetime,
    stop_event: asyncio.Event,
    heartbeat_interval_seconds: int,
) -> None:
    await _write_heartbeat(
        session_maker=session_maker,
        service_name=service_name,
        instance_id=instance_id,
        now=started_at,
        running=True,
    )
    while not stop_event.is_set():
        with suppress(TimeoutError):
            await asyncio.wait_for(
                stop_event.wait(), timeout=max(1, heartbeat_interval_seconds)
            )
        if stop_event.is_set():
            break
        await _write_heartbeat(
            session_maker=session_maker,
            service_name=service_name,
            instance_id=instance_id,
            now=datetime.now(UTC),
            running=True,
        )


async def run_worker_forever(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    service_name: str = DEFAULT_WORKER_SERVICE_NAME,
    instance_id: str | None = None,
    idle_sleep_seconds: float = 1.0,
    heartbeat_interval_seconds: int | None = None,
) -> None:
    """Run the Winoe worker loop forever."""
    resolved_instance_id = instance_id or _build_worker_instance_id()
    resolved_heartbeat_interval = (
        heartbeat_interval_seconds
        if heartbeat_interval_seconds is not None
        else settings.WORKER_HEARTBEAT_INTERVAL_SECONDS
    )
    started_at = datetime.now(UTC)
    stop_event = asyncio.Event()

    try:
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGINT, signal.SIGTERM):
            with suppress(NotImplementedError):
                loop.add_signal_handler(signum, stop_event.set)
    except RuntimeError:
        pass

    logger.info(
        "winoe_worker_started",
        extra={
            "service_name": service_name,
            "instance_id": resolved_instance_id,
            "heartbeat_interval_seconds": resolved_heartbeat_interval,
        },
    )
    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(
            session_maker=session_maker,
            service_name=service_name,
            instance_id=resolved_instance_id,
            started_at=started_at,
            stop_event=stop_event,
            heartbeat_interval_seconds=resolved_heartbeat_interval,
        )
    )
    failure: BaseException | None = None
    try:
        while not stop_event.is_set():
            handled = await worker_service.run_once(
                session_maker=session_maker,
                worker_id=resolved_instance_id,
            )
            if handled:
                await asyncio.sleep(0)
            else:
                with suppress(TimeoutError):
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=max(0.1, idle_sleep_seconds)
                    )
            if heartbeat_task.done():
                try:
                    heartbeat_task.result()
                except Exception:
                    logger.exception(
                        "winoe_worker_heartbeat_failed",
                        extra={
                            "service_name": service_name,
                            "instance_id": resolved_instance_id,
                        },
                    )
                    raise
    except BaseException as exc:
        failure = exc
    finally:
        stop_event.set()
        if not heartbeat_task.done():
            heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            if failure is None:
                failure = exc
            else:
                logger.exception(
                    "winoe_worker_heartbeat_failed_during_shutdown",
                    extra={
                        "service_name": service_name,
                        "instance_id": resolved_instance_id,
                    },
                )
        try:
            await _write_heartbeat(
                session_maker=session_maker,
                service_name=service_name,
                instance_id=resolved_instance_id,
                now=datetime.now(UTC),
                running=False,
            )
        except Exception as exc:
            if failure is None:
                failure = exc
            else:
                logger.exception(
                    "winoe_worker_stopped_write_failed",
                    extra={
                        "service_name": service_name,
                        "instance_id": resolved_instance_id,
                    },
                )
        logger.info(
            "winoe_worker_stopped",
            extra={
                "service_name": service_name,
                "instance_id": resolved_instance_id,
            },
        )
    if failure is not None:
        raise failure


__all__ = [
    "DEFAULT_WORKER_SERVICE_NAME",
    "_build_worker_instance_id",
    "WORKER_HEARTBEAT_STATUS_STOPPED",
    "is_worker_heartbeat_fresh",
    "run_worker_forever",
]
