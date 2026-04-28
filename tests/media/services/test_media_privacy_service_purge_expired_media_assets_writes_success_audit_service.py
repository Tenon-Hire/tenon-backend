from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_purge_expired_media_assets_writes_success_audit(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-purge-audit@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, trial=trial)

    now = datetime.now(UTC).replace(microsecond=0)
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/purge-audit.mp4"
        ),
        content_type="video/mp4",
        bytes_count=2048,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        retention_expires_at=now - timedelta(seconds=1),
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
        batch_limit=20,
        now=now,
    )

    audit = (
        await async_session.execute(
            select(MediaPurgeAudit).where(MediaPurgeAudit.media_id == recording.id)
        )
    ).scalar_one()
    assert result.purged_count == 1
    assert audit.candidate_session_id == candidate_session.id
    assert audit.trial_id == trial.id
    assert audit.purge_reason == "retention_expired"
    assert audit.actor_type == MEDIA_PURGE_ACTOR_SYSTEM
    assert audit.actor_id is None
    assert audit.outcome == "success"
    assert audit.error_summary is None
