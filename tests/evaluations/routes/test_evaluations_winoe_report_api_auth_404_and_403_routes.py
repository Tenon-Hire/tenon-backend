from __future__ import annotations

import pytest

from tests.evaluations.routes.evaluations_winoe_report_api_utils import *


@pytest.mark.asyncio
async def test_winoe_report_auth_404_and_403(
    async_client,
    async_session,
    auth_header_factory,
):
    owner, candidate_session = await _seed_completed_candidate_session(async_session)
    outsider = await create_talent_partner(
        async_session,
        email="winoe-report-outsider@test.com",
    )
    await async_session.commit()

    missing_post = await async_client.post(
        "/api/candidate_sessions/999999/winoe_report/generate",
        headers=auth_header_factory(owner),
    )
    assert missing_post.status_code == 404

    missing_get = await async_client.get(
        "/api/candidate_sessions/999999/winoe_report",
        headers=auth_header_factory(owner),
    )
    assert missing_get.status_code == 404

    forbidden_post = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report/generate",
        headers=auth_header_factory(outsider),
    )
    assert forbidden_post.status_code == 403

    forbidden_get = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report",
        headers=auth_header_factory(outsider),
    )
    assert forbidden_get.status_code == 403
