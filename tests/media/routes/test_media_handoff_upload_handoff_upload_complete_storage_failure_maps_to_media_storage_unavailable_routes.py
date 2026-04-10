from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_complete_storage_failure_maps_to_media_storage_unavailable(
    async_client, async_session, candidate_header_factory, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-complete-storage-failure@test.com"
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

    provider = _fake_storage_provider()

    def _raise_storage_error(*args, **kwargs):
        del args, kwargs
        raise StorageMediaError("storage down")

    monkeypatch.setattr(provider, "get_object_metadata", _raise_storage_error)

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 502
    assert complete_response.json()["errorCode"] == MEDIA_STORAGE_UNAVAILABLE
