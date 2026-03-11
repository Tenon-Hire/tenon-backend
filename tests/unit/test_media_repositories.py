from __future__ import annotations

import pytest

from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_UPLOADING,
)
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
