from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_purge_expired_media_assets_logs_without_sensitive_payload(
    async_session,
    caplog,
):
    caplog.set_level(
        "INFO", logger="app.media.services.media_services_media_privacy_service"
    )
    talent_partner = await create_talent_partner(
        async_session, email="privacy-purge-log@test.com"
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
            "recordings/purge-log.mp4"
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
        text="do-not-log-this-purge-transcript",
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

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert recording.id in result.purged_recording_ids
    assert f"mediaId={recording.id}" in log_text
    assert "do-not-log-this-purge-transcript" not in log_text
    assert "https://" not in log_text
