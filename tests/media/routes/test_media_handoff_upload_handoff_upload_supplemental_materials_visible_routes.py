from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_supplemental_materials_visible_in_detail(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-supplemental@test.com"
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
            "durationSeconds": 600,
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
                RecordingAsset.asset_kind == "recording",
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
        duration_seconds=600,
    )
    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 200, complete_response.text

    supplemental_init = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "application/pdf",
            "sizeBytes": 512,
            "filename": "slides.pdf",
            "assetType": "supplemental",
        },
    )
    assert supplemental_init.status_code == 200, supplemental_init.text
    supplemental_recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
                RecordingAsset.asset_kind == "supplemental",
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        supplemental_recording.storage_key,
        content_type=supplemental_recording.content_type,
        size_bytes=supplemental_recording.bytes,
    )
    supplemental_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": supplemental_init.json()["recordingId"]},
    )
    assert supplemental_complete.status_code == 200, supplemental_complete.text
    await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "supplemental/deleted.pdf"
        ),
        content_type="application/pdf",
        bytes_count=256,
        asset_kind="supplemental",
        status="deleted",
        commit=True,
    )

    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == task.id,
            )
        )
    ).scalar_one()
    detail_response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert detail_response.status_code == 200, detail_response.text
    body = detail_response.json()
    assert body["handoff"]["recordingId"] == init_response.json()["recordingId"]
    assert len(body["handoff"]["supplementalMaterials"]) == 1
    assert body["handoff"]["supplementalMaterials"][0]["assetKind"] == "supplemental"
    assert body["handoff"]["supplementalMaterials"][0]["downloadUrl"] is not None
