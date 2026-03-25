from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_recruiter_same_company_can_fetch_submission_detail(
    async_client, async_session
):
    company = await create_company(async_session, name="Shared Co")
    owner = await create_recruiter(
        async_session,
        email="company-owner@test.com",
        company=company,
    )
    teammate = await create_recruiter(
        async_session,
        email="company-teammate@test.com",
        company=company,
    )
    sim, tasks = await create_simulation(async_session, created_by=owner)
    candidate_session = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[0],
        content_text="answer",
    )

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": teammate.email},
    )
    assert response.status_code == 200, response.text
