from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_PURGED,
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_UPLOADING,
)
from app.repositories.submissions import repository as submissions_repo
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import (
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_PENDING,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


@pytest.mark.asyncio
async def test_recordings_repository_get_and_update_status(async_session):
    recruiter = await create_recruiter(async_session, email="recordings-repo@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

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
    recording.status = RECORDING_ASSET_STATUS_FAILED
    assert recordings_repo.is_downloadable(recording) is False
    recording.status = RECORDING_ASSET_STATUS_DELETED
    assert recordings_repo.is_downloadable(recording) is False
    recording.status = RECORDING_ASSET_STATUS_UPLOADED
    recording.deleted_at = datetime.now(UTC)
    assert recordings_repo.is_downloadable(recording) is False
    recording.status = RECORDING_ASSET_STATUS_PURGED
    assert recordings_repo.is_downloadable(recording) is False


@pytest.mark.asyncio
async def test_transcripts_repository_create_get_or_create_and_update(async_session):
    recruiter = await create_recruiter(async_session, email="transcripts-repo@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/transcript.mp4"
        ),
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )

    created, was_created = await transcripts_repo.get_or_create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_PENDING,
        commit=False,
    )
    assert was_created is True
    assert created.recording_id == recording.id

    fetched = await transcripts_repo.get_by_recording_id(async_session, recording.id)
    assert fetched is not None
    assert fetched.id == created.id

    existing, was_created_again = await transcripts_repo.get_or_create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_FAILED,
        commit=True,
    )
    assert was_created_again is False
    assert existing.id == created.id

    updated = await transcripts_repo.update_status(
        async_session,
        transcript=existing,
        status=TRANSCRIPT_STATUS_FAILED,
        commit=False,
    )
    assert updated.status == TRANSCRIPT_STATUS_FAILED

    persisted = await transcripts_repo.update_status(
        async_session,
        transcript=existing,
        status=TRANSCRIPT_STATUS_FAILED,
        commit=True,
    )
    assert persisted.status == TRANSCRIPT_STATUS_FAILED

    await transcripts_repo.update_transcript(
        async_session,
        transcript=persisted,
        last_error="provider timeout",
        model_name="mock-stt-v1",
        commit=True,
    )
    refreshed = await transcripts_repo.get_by_recording_id(async_session, recording.id)
    assert refreshed is not None
    assert refreshed.last_error == "provider timeout"
    assert refreshed.model_name == "mock-stt-v1"


@pytest.mark.asyncio
async def test_submissions_repository_handoff_create_and_update(async_session):
    recruiter = await create_recruiter(async_session, email="submissions-repo@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

    first_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/submission-a.mp4"
        ),
        content_type="video/mp4",
        bytes_count=500,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    second_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/submission-b.mp4"
        ),
        content_type="video/mp4",
        bytes_count=800,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )

    created = await submissions_repo.create_handoff_submission(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        recording_id=first_recording.id,
        submitted_at=datetime.now(UTC),
        commit=True,
    )
    assert created.recording_id == first_recording.id

    locked = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        for_update=True,
    )
    assert locked is not None
    assert locked.id == created.id

    updated_flush = await submissions_repo.update_handoff_submission(
        async_session,
        submission=created,
        recording_id=second_recording.id,
        submitted_at=datetime.now(UTC),
        commit=False,
    )
    assert updated_flush.recording_id == second_recording.id

    updated_commit = await submissions_repo.update_handoff_submission(
        async_session,
        submission=created,
        recording_id=first_recording.id,
        submitted_at=datetime.now(UTC),
        commit=True,
    )
    assert updated_commit.recording_id == first_recording.id


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
