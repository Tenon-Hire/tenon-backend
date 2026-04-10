from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_delete_recording_asset_forbidden_for_other_candidate(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-delete-403@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="owner@test.com",
    )
    other_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="other@test.com",
    )

    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=owner_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{owner_session.id}/tasks/{task.id}/"
            "recordings/delete-forbidden.mp4"
        ),
        content_type="video/mp4",
        bytes_count=512,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        await delete_recording_asset(
            async_session,
            recording_id=recording.id,
            candidate_session=other_session,
        )

    assert exc_info.value.status_code == 403
