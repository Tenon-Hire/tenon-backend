from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.media.services.media_services_media_retention_jobs_service import (
    MEDIA_RETENTION_PURGE_JOB_TYPE,
)
from app.shared.jobs import worker
from app.shared.jobs.handlers import media_retention_purge as handler


class _SessionMaker:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_media_retention_purge_handler_maps_payload(monkeypatch):
    calls = {}

    async def _purge(db, *, storage_provider, retention_days, batch_limit, **kwargs):
        calls["db"] = db
        calls["storage_provider"] = storage_provider
        calls["retention_days"] = retention_days
        calls["batch_limit"] = batch_limit
        calls["kwargs"] = kwargs
        return SimpleNamespace(
            scanned_count=4,
            purged_count=3,
            skipped_count=1,
            failed_count=0,
        )

    monkeypatch.setattr(handler, "async_session_maker", lambda: _SessionMaker("db"))
    monkeypatch.setattr(handler, "get_storage_media_provider", lambda: "provider")
    monkeypatch.setattr(handler, "purge_expired_media_assets", _purge)

    result = await handler.handle_media_retention_purge(
        {"retentionDays": 7, "batchLimit": 50}
    )

    assert calls == {
        "db": "db",
        "storage_provider": "provider",
        "retention_days": 7,
        "batch_limit": 50,
        "kwargs": {},
    }
    assert result == {
        "scannedCount": 4,
        "purgedCount": 3,
        "skippedCount": 1,
        "failedCount": 0,
    }


def test_media_retention_purge_is_registered_builtin_handler():
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        assert worker.has_handler(MEDIA_RETENTION_PURGE_JOB_TYPE)
    finally:
        worker.clear_handlers()
