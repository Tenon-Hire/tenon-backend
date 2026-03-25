from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_detail_includes_status_and_lifecycle_timestamps(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="detail-lifecycle@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
    )
    sim_id = created["id"]

    detail = await async_client.get(
        f"/api/simulations/{sim_id}",
        headers=auth_header_factory(recruiter),
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "ready_for_review"
    assert body["generatingAt"] is not None
    assert body["readyForReviewAt"] is not None
    assert body["activatedAt"] is None
    assert body["scenarioVersionSummary"]["templateKey"] == "python-fastapi"

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    detail_after = await async_client.get(
        f"/api/simulations/{sim_id}",
        headers=auth_header_factory(recruiter),
    )
    assert detail_after.status_code == 200, detail_after.text
    body_after = detail_after.json()
    assert body_after["status"] == "active_inviting"
    assert body_after["activatedAt"] is not None
