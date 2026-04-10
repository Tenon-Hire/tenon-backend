from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.talent_partners.routes.admin_routes import demo_ops
from app.talent_partners.schemas.talent_partners_schemas_talent_partners_admin_ops_schema import (
    MediaRetentionPurgeRequest,
)


@pytest.mark.asyncio
async def test_purge_media_retention_route_maps_service_result(monkeypatch):
    async def _purge(
        db,
        *,
        storage_provider,
        retention_days: int | None,
        batch_limit: int,
    ):
        del db, storage_provider
        assert retention_days == 30
        assert batch_limit == 50
        return SimpleNamespace(
            scanned_count=3,
            purged_count=2,
            failed_count=1,
            purged_recording_ids=[11, 12],
        )

    monkeypatch.setattr(demo_ops, "purge_expired_media_assets", _purge)

    result = await demo_ops.purge_media_retention(
        payload=MediaRetentionPurgeRequest(retentionDays=30, batchLimit=50),
        db=None,
        actor=SimpleNamespace(),
        storage_provider=SimpleNamespace(),
    )

    assert result.status == "ok"
    assert result.scannedCount == 3
    assert result.purgedCount == 2
    assert result.failedCount == 1
    assert result.purgedRecordingIds == [11, 12]
