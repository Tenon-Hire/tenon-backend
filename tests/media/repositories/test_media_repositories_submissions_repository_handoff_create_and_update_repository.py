from __future__ import annotations

import pytest

from tests.media.repositories.media_repositories_utils import *


@pytest.mark.asyncio
async def test_submissions_repository_handoff_create_and_update(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="submissions-repo@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, trial=sim)

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
