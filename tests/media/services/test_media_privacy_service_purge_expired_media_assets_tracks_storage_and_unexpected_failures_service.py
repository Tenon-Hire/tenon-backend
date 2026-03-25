from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_purge_expired_media_assets_tracks_storage_and_unexpected_failures(
    async_session,
    monkeypatch,
):
    candidates = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    async def _expired(*_args, **_kwargs):
        return candidates

    async def _for_update(_db, recording_id: int):
        return SimpleNamespace(
            id=recording_id,
            status=RECORDING_ASSET_STATUS_UPLOADED,
            purged_at=None,
            storage_key=(
                f"candidate-sessions/1/tasks/1/recordings/failure-{recording_id}.mp4"
            ),
        )

    class _BrokenProvider:
        def __init__(self):
            self.calls = 0

        def delete_object(self, key: str) -> None:
            del key
            self.calls += 1
            if self.calls == 1:
                raise StorageMediaError("storage down")
            raise RuntimeError("unexpected failure")

    monkeypatch.setattr(recordings_repo, "get_expired_for_retention", _expired)
    monkeypatch.setattr(recordings_repo, "get_by_id_for_update", _for_update)

    result = await purge_expired_media_assets(
        async_session,
        storage_provider=_BrokenProvider(),
        retention_days=1,
        batch_limit=10,
        now=datetime.now(UTC),
    )

    assert result.scanned_count == 2
    assert result.purged_count == 0
    assert result.failed_count == 2
