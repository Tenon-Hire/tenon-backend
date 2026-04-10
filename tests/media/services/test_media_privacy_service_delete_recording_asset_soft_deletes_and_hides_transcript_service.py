from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_delete_recording_asset_soft_deletes_and_hides_transcript(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-delete@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, trial=sim)

    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/delete.mp4"
        ),
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="sensitive transcript",
        segments_json=[{"startMs": 0, "endMs": 1, "text": "hidden"}],
        model_name="model",
        commit=True,
    )

    await delete_recording_asset(
        async_session,
        recording_id=recording.id,
        candidate_session=candidate_session,
    )
    await delete_recording_asset(
        async_session,
        recording_id=recording.id,
        candidate_session=candidate_session,
    )

    refreshed = await recordings_repo.get_by_id(async_session, recording.id)
    transcript = await transcripts_repo.get_by_recording_id(
        async_session,
        recording.id,
        include_deleted=True,
    )

    assert refreshed is not None
    assert refreshed.deleted_at is not None
    assert recordings_repo.is_downloadable(refreshed) is False
    assert transcript is not None
    assert transcript.deleted_at is not None
    assert transcript.text is None
    assert transcript.segments_json is None
