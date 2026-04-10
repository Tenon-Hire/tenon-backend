from __future__ import annotations

import pytest

from tests.media.repositories.media_repositories_utils import *


@pytest.mark.asyncio
async def test_recordings_repository_get_and_update_status(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="recordings-repo@test.com"
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
            "recordings/repo.mp4"
        ),
        content_type="video/mp4",
        bytes_count=512,
        status=RECORDING_ASSET_STATUS_UPLOADING,
        commit=True,
    )
    fetched = await recordings_repo.get_by_id(async_session, recording.id)
    assert fetched is not None
    assert fetched.id == recording.id

    updated = await recordings_repo.update_status(
        async_session,
        recording=recording,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    assert updated.status == RECORDING_ASSET_STATUS_UPLOADED

    unchanged = await recordings_repo.update_status(
        async_session,
        recording=recording,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=False,
    )
    assert unchanged.status == RECORDING_ASSET_STATUS_UPLOADED
    assert recordings_repo.is_downloadable(unchanged) is True
    assert recordings_repo.is_downloadable(None) is False
    assert recordings_repo.is_deleted_or_purged(None) is False
    recording.status = RECORDING_ASSET_STATUS_FAILED
    assert recordings_repo.is_downloadable(recording) is False
    recording.status = RECORDING_ASSET_STATUS_DELETED
    assert recordings_repo.is_downloadable(recording) is False
    recording.status = RECORDING_ASSET_STATUS_UPLOADED
    recording.deleted_at = datetime.now(UTC)
    assert recordings_repo.is_downloadable(recording) is False
    recording.status = RECORDING_ASSET_STATUS_PURGED
    assert recordings_repo.is_downloadable(recording) is False
