from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_complete_is_idempotent_and_creates_transcript(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-complete@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
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
    recording_id = init_response.json()["recordingId"]
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    first_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert first_complete.status_code == 200, first_complete.text
    assert first_complete.json()["status"] == RECORDING_ASSET_STATUS_UPLOADED

    second_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert second_complete.status_code == 200, second_complete.text
    assert second_complete.json()["status"] == RECORDING_ASSET_STATUS_UPLOADED

    recording_after = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    transcript = (
        await async_session.execute(
            select(Transcript).where(Transcript.recording_id == recording_after.id)
        )
    ).scalar_one()
    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == task.id,
            )
        )
    ).scalar_one()
    jobs = (
        (
            await async_session.execute(
                select(Job).where(
                    Job.job_type == TRANSCRIBE_RECORDING_JOB_TYPE,
                    Job.idempotency_key
                    == transcribe_recording_idempotency_key(recording_after.id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert recording_after.status == RECORDING_ASSET_STATUS_UPLOADED
    assert transcript.status == TRANSCRIPT_STATUS_PENDING
    assert submission.recording_id == recording_after.id
    assert len(jobs) == 1
