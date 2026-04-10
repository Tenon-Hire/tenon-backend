from __future__ import annotations

import pytest

from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_put_task_draft_rejects_oversized_content_text(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="draft-size-text@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session, trial=sim, status="in_progress", with_default_schedule=True
    )
    await async_session.commit()
    oversized_text = "x" * (200 * 1024 + 1)
    response = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=candidate_header_factory(candidate_session),
        json={"contentText": oversized_text},
    )
    assert response.status_code == 413, response.text
    body = response.json()
    assert body["errorCode"] == "DRAFT_CONTENT_TOO_LARGE"
    assert body["details"]["field"] == "contentText"


@pytest.mark.asyncio
async def test_put_task_draft_rejects_oversized_content_json(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="draft-size-json@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session, trial=sim, status="in_progress", with_default_schedule=True
    )
    await async_session.commit()
    oversized_json = {"blob": "y" * (200 * 1024 + 128)}
    response = await async_client.put(
        f"/api/tasks/{tasks[0].id}/draft",
        headers=candidate_header_factory(candidate_session),
        json={"contentJson": oversized_json},
    )
    assert response.status_code == 413, response.text
    body = response.json()
    assert body["errorCode"] == "DRAFT_CONTENT_TOO_LARGE"
    assert body["details"]["field"] == "contentJson"
