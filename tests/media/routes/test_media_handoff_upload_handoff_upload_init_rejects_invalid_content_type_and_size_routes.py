from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_init_rejects_invalid_content_type_and_size(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-invalid@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    bad_type = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "application/pdf",
            "sizeBytes": 1_024,
            "filename": "demo.pdf",
        },
    )
    assert bad_type.status_code == 422

    too_big = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 100 * 1024 * 1024 + 1,
            "filename": "demo.mp4",
        },
    )
    assert too_big.status_code == 413
    assert too_big.json()["errorCode"] == "REQUEST_TOO_LARGE"
