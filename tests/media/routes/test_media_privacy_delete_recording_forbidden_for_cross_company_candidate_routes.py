from __future__ import annotations

import pytest

from tests.media.routes.media_privacy_api_utils import *


@pytest.mark.asyncio
async def test_delete_recording_forbidden_for_cross_company_candidate(
    async_client,
    async_session,
    candidate_header_factory,
):
    company_a = await create_company(async_session, name="Delete Co A")
    company_b = await create_company(async_session, name="Delete Co B")
    talent_partner_a = await create_talent_partner(
        async_session,
        email="privacy-delete-company-a@test.com",
        company=company_a,
    )
    talent_partner_b = await create_talent_partner(
        async_session,
        email="privacy-delete-company-b@test.com",
        company=company_b,
    )
    sim_a, tasks_a = await create_trial(async_session, created_by=talent_partner_a)
    sim_b, _tasks_b = await create_trial(async_session, created_by=talent_partner_b)
    task_a = _handoff_task(tasks_a)
    owner_session = await create_candidate_session(
        async_session,
        trial=sim_a,
        invite_email="delete-cross-owner@test.com",
        status="in_progress",
    )
    other_company_session = await create_candidate_session(
        async_session,
        trial=sim_b,
        invite_email="delete-cross-other@test.com",
        status="in_progress",
    )
    recording = await _seed_uploaded_recording(
        async_session,
        candidate_session=owner_session,
        task_id=task_a.id,
        filename="forbidden-cross-company.mp4",
    )

    response = await async_client.post(
        f"/api/recordings/rec_{recording.id}/delete",
        headers=candidate_header_factory(other_company_session),
    )

    assert response.status_code == 403
