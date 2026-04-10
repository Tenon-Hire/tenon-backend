from __future__ import annotations

import pytest

from tests.media.repositories.media_repositories_utils import *


@pytest.mark.asyncio
async def test_recordings_repository_retention_helpers(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="recordings-retention@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, trial=sim)

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


@pytest.mark.asyncio
async def test_recordings_repository_mark_deleted_and_mark_purged_preserve_terminal_fields(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="recordings-terminal-paths@test.com"
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
            "recordings/terminal.mp4"
        ),
        content_type="video/mp4",
        bytes_count=100,
        status=RECORDING_ASSET_STATUS_PURGED,
        created_at=datetime.now(UTC).replace(microsecond=0),
        commit=True,
    )
    original_purged_at = datetime.now(UTC) - timedelta(days=1)
    recording.purged_at = original_purged_at
    recording.deleted_at = datetime.now(UTC) - timedelta(days=2)
    await async_session.commit()

    await recordings_repo.mark_deleted(
        async_session,
        recording=recording,
        commit=False,
    )
    assert recording.status == RECORDING_ASSET_STATUS_PURGED

    await recordings_repo.mark_purged(
        async_session,
        recording=recording,
        now=datetime.now(UTC),
        commit=False,
    )
    assert recording.purged_at == original_purged_at
