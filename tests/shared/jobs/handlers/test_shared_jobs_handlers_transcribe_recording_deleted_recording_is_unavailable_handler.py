from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_utils import *


@pytest.mark.asyncio
async def test_transcribe_recording_handler_deleted_recording_is_unavailable(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="transcribe-deleted@test.com"
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
            "recordings/transcribe-deleted.mp4"
        ),
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_DELETED,
        commit=True,
    )
    recording.deleted_at = recording.created_at
    await async_session.commit()

    result = await handler.handle_transcribe_recording({"recordingId": recording.id})
    assert result["status"] == "recording_unavailable"
