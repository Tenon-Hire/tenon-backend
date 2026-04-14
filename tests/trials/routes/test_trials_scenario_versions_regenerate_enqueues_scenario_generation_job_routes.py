from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_enqueues_scenario_generation_job(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-job-queue@test.com"
    )
    sim_id = await _create_trial(
        async_client, async_session, auth_header_factory(talent_partner)
    )
    headers = auth_header_factory(talent_partner)
    await _approve_trial(async_client, sim_id=sim_id, headers=headers)
    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    regenerate = await async_client.post(
        f"/api/trials/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert regenerate.status_code == 200, regenerate.text
    payload = regenerate.json()

    job = await async_session.get(Job, payload["jobId"])
    assert job is not None
    assert job.status == JOB_STATUS_QUEUED
    assert job.payload_json["trialId"] == sim_id
    assert job.payload_json["scenarioVersionId"] == payload["scenarioVersionId"]
