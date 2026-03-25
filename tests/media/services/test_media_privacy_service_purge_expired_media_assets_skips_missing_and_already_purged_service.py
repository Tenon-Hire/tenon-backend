from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_purge_expired_media_assets_skips_missing_and_already_purged(
    async_session,
    monkeypatch,
):
    candidates = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    async def _expired(*_args, **_kwargs):
        return candidates

    async def _for_update(_db, recording_id: int):
        if recording_id == 1:
            return None
        return SimpleNamespace(
            id=2,
            status=RECORDING_ASSET_STATUS_PURGED,
            purged_at=datetime.now(UTC),
            storage_key="candidate-sessions/1/tasks/1/recordings/purged.mp4",
        )

    monkeypatch.setattr(recordings_repo, "get_expired_for_retention", _expired)
    monkeypatch.setattr(recordings_repo, "get_by_id_for_update", _for_update)

    result = await purge_expired_media_assets(
        async_session,
        storage_provider=FakeStorageMediaProvider(),
        retention_days=1,
        batch_limit=10,
        now=datetime.now(UTC),
    )

    assert result.scanned_count == 2
    assert result.purged_count == 0
    assert result.failed_count == 0
