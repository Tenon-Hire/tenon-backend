from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_terminated_hidden_by_default_in_simulation_and_candidate_lists(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="filter@test.com")
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
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert invite.status_code == 200, invite.text

    terminated = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminated.status_code == 200, terminated.text

    simulations_default = await async_client.get(
        "/api/simulations", headers=auth_header_factory(recruiter)
    )
    assert simulations_default.status_code == 200, simulations_default.text
    assert all(row["id"] != sim_id for row in simulations_default.json())

    simulations_including = await async_client.get(
        "/api/simulations?includeTerminated=true",
        headers=auth_header_factory(recruiter),
    )
    assert simulations_including.status_code == 200, simulations_including.text
    assert any(row["id"] == sim_id for row in simulations_including.json())

    candidates_default = await async_client.get(
        f"/api/simulations/{sim_id}/candidates",
        headers=auth_header_factory(recruiter),
    )
    assert candidates_default.status_code == 404

    candidates_including = await async_client.get(
        f"/api/simulations/{sim_id}/candidates?includeTerminated=true",
        headers=auth_header_factory(recruiter),
    )
    assert candidates_including.status_code == 200, candidates_including.text
    assert len(candidates_including.json()) == 1
