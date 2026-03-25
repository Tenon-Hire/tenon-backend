from __future__ import annotations

import pytest

from tests.media.repositories.media_repositories_utils import *


@pytest.mark.asyncio
async def test_recordings_repository_retention_helpers(async_session):
    recruiter = await create_recruiter(
        async_session, email="recordings-retention@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

    old_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/old.mp4"
        ),
        content_type="video/mp4",
        bytes_count=100,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        created_at=datetime.now(UTC).replace(microsecond=0),
        commit=True,
    )
    old_recording.created_at = datetime.now(UTC) - timedelta(days=10)
    await async_session.commit()

    expired = await recordings_repo.get_expired_for_retention(
        async_session,
        retention_days=5,
    )
    assert {item.id for item in expired} == {old_recording.id}

    await recordings_repo.mark_deleted(
        async_session,
        recording=old_recording,
        commit=True,
    )
    assert old_recording.deleted_at is not None
    assert old_recording.status == RECORDING_ASSET_STATUS_DELETED

    await recordings_repo.mark_purged(
        async_session,
        recording=old_recording,
        commit=True,
    )
    assert old_recording.purged_at is not None
    assert old_recording.status == RECORDING_ASSET_STATUS_PURGED
