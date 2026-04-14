from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.shared.jobs import shared_jobs_worker_heartbeat_service as heartbeat_service
from app.shared.jobs.repositories import repository as jobs_repo


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@pytest.mark.asyncio
async def test_upsert_worker_heartbeat_creates_and_updates(async_session):
    started_at = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    first = await jobs_repo.upsert_worker_heartbeat(
        async_session,
        service_name="winoe-worker",
        instance_id="worker-1",
        now=started_at,
    )

    assert first.service_name == "winoe-worker"
    assert first.instance_id == "worker-1"
    assert first.status == "running"
    assert _to_utc(first.started_at) == started_at
    assert _to_utc(first.last_heartbeat_at) == started_at

    updated_at = started_at + timedelta(seconds=30)
    second = await jobs_repo.upsert_worker_heartbeat(
        async_session,
        service_name="winoe-worker",
        instance_id="worker-1",
        now=updated_at,
    )

    assert _to_utc(second.started_at) == started_at
    assert _to_utc(second.last_heartbeat_at) == updated_at
    assert second.status == "running"


@pytest.mark.asyncio
async def test_latest_worker_heartbeat_helper_and_freshness(async_session):
    newer = datetime(2026, 4, 14, 12, 5, tzinfo=UTC)
    older = newer - timedelta(minutes=5)
    await jobs_repo.upsert_worker_heartbeat(
        async_session,
        service_name="winoe-worker",
        instance_id="worker-old",
        now=older,
    )
    await jobs_repo.upsert_worker_heartbeat(
        async_session,
        service_name="winoe-worker",
        instance_id="worker-new",
        now=newer,
    )

    latest = await jobs_repo.get_latest_worker_heartbeat(
        async_session, service_name="winoe-worker"
    )
    assert latest is not None
    assert latest.instance_id == "worker-new"
    assert heartbeat_service.is_worker_heartbeat_fresh(
        SimpleNamespace(last_heartbeat_at=newer),
        now=newer + timedelta(seconds=30),
        stale_after_seconds=60,
    )
    assert heartbeat_service.is_worker_heartbeat_fresh(
        SimpleNamespace(last_heartbeat_at=datetime(2026, 4, 14, 12, 4, 30)),
        now=newer,
        stale_after_seconds=60,
    )
    assert not heartbeat_service.is_worker_heartbeat_fresh(
        SimpleNamespace(last_heartbeat_at=older),
        now=newer,
        stale_after_seconds=60,
    )


@pytest.mark.asyncio
async def test_worker_heartbeat_rejects_blank_fields_and_can_mark_stopped(
    async_session,
):
    with pytest.raises(ValueError):
        await jobs_repo.upsert_worker_heartbeat(
            async_session,
            service_name=" ",
            instance_id="worker-blank",
            now=datetime(2026, 4, 14, 12, 10, tzinfo=UTC),
        )

    stopped_at = datetime(2026, 4, 14, 12, 11, tzinfo=UTC)
    stopped = await jobs_repo.mark_worker_stopped(
        async_session,
        service_name="winoe-worker",
        instance_id="worker-stopped",
        now=stopped_at,
    )

    assert stopped.status == heartbeat_service.WORKER_HEARTBEAT_STATUS_STOPPED
    assert _to_utc(stopped.last_heartbeat_at) == stopped_at


@pytest.mark.asyncio
async def test_get_latest_worker_heartbeat_returns_none_when_missing(async_session):
    latest = await jobs_repo.get_latest_worker_heartbeat(
        async_session, service_name="missing-worker"
    )

    assert latest is None


@pytest.mark.asyncio
async def test_worker_heartbeat_rejects_overlong_service_name(async_session):
    with pytest.raises(ValueError):
        await jobs_repo.upsert_worker_heartbeat(
            async_session,
            service_name="x" * 101,
            instance_id="worker-overlong",
            now=datetime(2026, 4, 14, 12, 12, tzinfo=UTC),
        )
