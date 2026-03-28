from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_recruiter_get_api_utils import *


@pytest.mark.asyncio
async def test_missing_submission_returns_404(
    async_client, async_session: AsyncSession
):
    recruiter = await create_recruiter(
        async_session, email="recruiter1@test.com", name="Recruiter One"
    )

    resp = await async_client.get(
        "/api/submissions/999999",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert resp.status_code == 404
