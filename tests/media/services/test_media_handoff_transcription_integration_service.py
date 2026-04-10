from __future__ import annotations

import pytest

from app.media.repositories.recordings import repository as recordings_repo
from tests.media.services.media_handoff_transcription_integration_utils import (
    assert_transcription_job_and_outputs,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


@pytest.mark.asyncio
async def test_handoff_upload_complete_enqueue_and_worker_transcribes(
    async_client,
    async_session,
    candidate_header_factory,
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-int@test.com"
    )
    talent_partner_email = talent_partner.email
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
        consent_version="mvp1",
        ai_notice_version="mvp1",
    )
    candidate_session_id = candidate_session.id
    task_id = task.id
    await async_session.commit()

    headers = candidate_header_factory(candidate_session)
    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_048,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text

    recording_id_value = init_response.json()["recordingId"]
    recording = await recordings_repo.get_latest_for_task_session(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert recording is not None

    from app.integrations.storage_media import get_storage_media_provider

    provider = get_storage_media_provider()
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id_value},
    )
    assert complete_response.status_code == 200, complete_response.text

    await assert_transcription_job_and_outputs(
        async_client,
        async_session,
        talent_partner_email=talent_partner_email,
        recording=recording,
        recording_id_value=recording_id_value,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
    )
