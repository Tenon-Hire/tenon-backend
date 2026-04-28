from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_purge_expired_media_assets_missing_storage_is_idempotent(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-purge-missing-storage@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, trial=trial)

    now = datetime.now(UTC).replace(microsecond=0)

    async def _recording(name: str):
        recording = await recordings_repo.create_recording_asset(
            async_session,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            storage_key=(
                f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
                f"recordings/{name}.mp4"
            ),
            content_type="video/mp4",
            bytes_count=2048,
            status=RECORDING_ASSET_STATUS_UPLOADED,
            retention_expires_at=now - timedelta(seconds=1),
            commit=True,
        )
        await transcripts_repo.create_transcript(
            async_session,
            recording_id=recording.id,
            status=TRANSCRIPT_STATUS_READY,
            text=f"transcript-{name}",
            segments_json=[{"text": f"segment-{name}"}],
            commit=True,
        )
        return recording

    missing_recording = await _recording("missing")
    present_recording = await _recording("present")
    provider = FakeStorageMediaProvider()
    provider.set_object_metadata(
        present_recording.storage_key,
        content_type=present_recording.content_type,
        size_bytes=present_recording.bytes,
    )

    result = await purge_expired_media_assets(
        async_session,
        storage_provider=provider,
        batch_limit=20,
        now=now,
    )

    refreshed_missing = await recordings_repo.get_by_id(
        async_session, missing_recording.id
    )
    missing_transcript = await transcripts_repo.get_by_recording_id(
        async_session,
        missing_recording.id,
        include_deleted=True,
    )
    audits = (
        (
            await async_session.execute(
                select(MediaPurgeAudit).where(
                    MediaPurgeAudit.media_id.in_(
                        [missing_recording.id, present_recording.id]
                    )
                )
            )
        )
        .scalars()
        .all()
    )

    assert result.scanned_count == 2
    assert result.purged_count == 2
    assert result.failed_count == 0
    assert set(result.purged_recording_ids) == {
        missing_recording.id,
        present_recording.id,
    }
    assert refreshed_missing is not None
    assert refreshed_missing.status == RECORDING_ASSET_STATUS_PURGED
    assert (
        refreshed_missing.purge_reason == RECORDING_ASSET_PURGE_REASON_RETENTION_EXPIRED
    )
    assert missing_transcript is not None
    assert missing_transcript.text is None
    assert missing_transcript.segments_json is None
    assert missing_transcript.deleted_at is not None
    assert len(audits) == 2
    assert {audit.outcome for audit in audits} == {"success"}
    assert {audit.actor_type for audit in audits} == {MEDIA_PURGE_ACTOR_SYSTEM}
