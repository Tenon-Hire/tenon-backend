from __future__ import annotations

import pytest

from tests.media.routes.media_privacy_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_complete_blocked_without_consent(
    async_client,
    async_session,
    candidate_header_factory,
):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-no-consent@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    headers = candidate_header_factory(candidate_session)
    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1024,
            "filename": "consent-required.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text

    provider = _fake_storage_provider()
    recording_asset = (
        (
            await async_session.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session.id,
                    RecordingAsset.task_id == task.id,
                )
                .order_by(RecordingAsset.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert recording_asset is not None
    provider.set_object_metadata(
        recording_asset.storage_key,
        content_type=recording_asset.content_type,
        size_bytes=recording_asset.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 409
    assert (
        complete_response.json()["detail"]
        == "Consent is required before upload completion"
    )
