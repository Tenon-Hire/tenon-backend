from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_candidate_token_resolve_and_claim_hidden_after_termination(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="token-hide@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
    )
    sim_id = created["id"]

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "hidden@example.com"},
    )
    assert invite.status_code == 200, invite.text
    token = invite.json()["token"]

    terminate = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminate.status_code == 200, terminate.text

    resolve = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": "Bearer candidate:hidden@example.com"},
    )
    assert resolve.status_code == 404, resolve.text
    assert resolve.json()["detail"] == "Invalid invite token"

    claim = await async_client.post(
        f"/api/candidate/session/{token}/claim",
        headers={"Authorization": "Bearer candidate:hidden@example.com"},
    )
    assert claim.status_code == 404, claim.text
    assert claim.json()["detail"] == "Invalid invite token"
