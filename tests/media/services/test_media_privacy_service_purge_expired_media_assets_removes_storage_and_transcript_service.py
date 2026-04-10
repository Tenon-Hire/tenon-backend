from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_purge_expired_media_assets_removes_storage_and_transcript(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-purge@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, trial=sim)

    now = datetime.now(UTC).replace(microsecond=0)
    old_created_at = now - timedelta(days=20)
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/purge.mp4"
        ),
        content_type="video/mp4",
        bytes_count=2048,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        created_at=old_created_at,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="purge me",
        commit=True,
    )

    provider = FakeStorageMediaProvider()
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    result = await purge_expired_media_assets(
        async_session,
        storage_provider=provider,
        retention_days=10,
        batch_limit=20,
        now=now,
    )

    refreshed = await recordings_repo.get_by_id(async_session, recording.id)
    transcript = await transcripts_repo.get_by_recording_id(
        async_session,
        recording.id,
        include_deleted=True,
    )

    assert result.scanned_count >= 1
    assert recording.id in result.purged_recording_ids
    assert result.purged_count == 1
    assert result.failed_count == 0
    assert provider.get_object_metadata(recording.storage_key) is None
    assert refreshed is not None
    assert refreshed.status == RECORDING_ASSET_STATUS_PURGED
    assert refreshed.purged_at is not None
    assert transcript is None
