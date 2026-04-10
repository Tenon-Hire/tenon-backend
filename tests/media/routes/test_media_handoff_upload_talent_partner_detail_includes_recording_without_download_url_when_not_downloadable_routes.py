from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_detail_includes_recording_without_download_url_when_not_downloadable(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-detail-uploading@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session, trial=sim, status="in_progress"
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff summary",
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/seed-uploading.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4_096,
        status=RECORDING_ASSET_STATUS_UPLOADING,
        commit=True,
    )
    submission.recording_id = recording.id
    await async_session.commit()

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADING
    assert body["recording"]["downloadUrl"] is None
    assert body["transcript"] is None
    assert body["handoff"]["recordingId"] == f"rec_{recording.id}"
    assert body["handoff"]["downloadUrl"] is None
