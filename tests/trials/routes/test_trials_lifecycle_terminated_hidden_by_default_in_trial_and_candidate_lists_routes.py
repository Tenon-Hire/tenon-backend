from __future__ import annotations

import pytest

from tests.trials.routes.trials_lifecycle_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_terminated_hidden_by_default_in_trial_and_candidate_lists(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(async_session, email="filter@test.com")
    created = await _create_trial_via_api(
        async_client, async_session, auth_header_factory(talent_partner)
    )
    sim_id = created["id"]
    await _approve_trial(
        async_client, sim_id=sim_id, headers=auth_header_factory(talent_partner)
    )

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=auth_header_factory(talent_partner),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert invite.status_code == 200, invite.text

    terminated = await async_client.post(
        f"/api/trials/{sim_id}/terminate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert terminated.status_code == 200, terminated.text

    trials_default = await async_client.get(
        "/api/trials", headers=auth_header_factory(talent_partner)
    )
    assert trials_default.status_code == 200, trials_default.text
    assert all(row["id"] != sim_id for row in trials_default.json())

    trials_including = await async_client.get(
        "/api/trials?includeTerminated=true",
        headers=auth_header_factory(talent_partner),
    )
    assert trials_including.status_code == 200, trials_including.text
    assert any(row["id"] == sim_id for row in trials_including.json())

    candidates_default = await async_client.get(
        f"/api/trials/{sim_id}/candidates",
        headers=auth_header_factory(talent_partner),
    )
    assert candidates_default.status_code == 404

    candidates_including = await async_client.get(
        f"/api/trials/{sim_id}/candidates?includeTerminated=true",
        headers=auth_header_factory(talent_partner),
    )
    assert candidates_including.status_code == 200, candidates_including.text
    assert len(candidates_including.json()) == 1
