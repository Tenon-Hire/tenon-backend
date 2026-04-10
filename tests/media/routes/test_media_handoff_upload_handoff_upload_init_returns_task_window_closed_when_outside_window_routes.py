from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_init_returns_task_window_closed_when_outside_window(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-window-init@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=False,
    )
    _set_closed_windows(candidate_session)
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(candidate_session),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "demo.mp4",
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["errorCode"] == "TASK_WINDOW_CLOSED"
