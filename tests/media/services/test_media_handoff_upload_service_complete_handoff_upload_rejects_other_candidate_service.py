from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_other_candidate(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="service-owner@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="owner@test.com",
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    other_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="other@test.com",
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    await async_session.commit()

    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=owner_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=other_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 403
