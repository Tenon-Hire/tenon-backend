from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_data_request_purges_only_associated_candidate_media(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-data-request@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    target_session = await create_candidate_session(async_session, trial=trial)
    other_session = await create_candidate_session(
        async_session, trial=trial, invite_email="other-data-request@test.com"
    )
    provider = FakeStorageMediaProvider()

    async def _recording(candidate_session, name: str):
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
            commit=True,
        )
        provider.set_object_metadata(
            recording.storage_key,
            content_type=recording.content_type,
            size_bytes=recording.bytes,
        )
        await transcripts_repo.create_transcript(
            async_session,
            recording_id=recording.id,
            status=TRANSCRIPT_STATUS_READY,
            text=f"transcript-{name}",
            commit=True,
        )
        return recording

    target_recording = await _recording(target_session, "target")
    other_recording = await _recording(other_session, "other")

    first = await purge_candidate_session_media_for_data_request(
        async_session,
        candidate_session_id=target_session.id,
        storage_provider=provider,
        actor_id="privacy-operator",
    )
    second = await purge_candidate_session_media_for_data_request(
        async_session,
        candidate_session_id=target_session.id,
        storage_provider=provider,
        actor_id="privacy-operator",
    )

    refreshed_target = await recordings_repo.get_by_id(
        async_session, target_recording.id
    )
    refreshed_other = await recordings_repo.get_by_id(async_session, other_recording.id)
    target_transcript = await transcripts_repo.get_by_recording_id(
        async_session, target_recording.id, include_deleted=True
    )
    audits = (
        (
            await async_session.execute(
                select(MediaPurgeAudit).where(
                    MediaPurgeAudit.media_id == target_recording.id
                )
            )
        )
        .scalars()
        .all()
    )

    assert first.purged_count == 1
    assert second.scanned_count == 0
    assert refreshed_target.status == RECORDING_ASSET_STATUS_PURGED
    assert refreshed_target.purge_reason == "data_request"
    assert target_transcript.text is None
    assert refreshed_other.status == RECORDING_ASSET_STATUS_UPLOADED
    assert provider.get_object_metadata(other_recording.storage_key) is not None
    assert len(audits) == 1
    assert audits[0].purge_reason == RECORDING_ASSET_PURGE_REASON_DATA_REQUEST
    assert audits[0].actor_type == MEDIA_PURGE_ACTOR_OPERATOR
    assert audits[0].actor_id == "privacy-operator"
