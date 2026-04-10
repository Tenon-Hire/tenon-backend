from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_talent_partner_get_api_utils import *


@pytest.mark.asyncio
async def test_missing_submission_returns_404(
    async_client, async_session: AsyncSession
):
    talent_partner = await create_talent_partner(
        async_session, email="talent_partner1@test.com", name="TalentPartner One"
    )

    resp = await async_client.get(
        "/api/submissions/999999",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert resp.status_code == 404
