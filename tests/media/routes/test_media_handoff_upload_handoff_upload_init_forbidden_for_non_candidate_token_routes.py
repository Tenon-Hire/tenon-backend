from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_init_forbidden_for_non_candidate_token(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-token@test.com"
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

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(
            candidate_session, token=f"talent_partner:{talent_partner.email}"
        ),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 100,
            "filename": "demo.mp4",
        },
    )
    assert response.status_code == 403
