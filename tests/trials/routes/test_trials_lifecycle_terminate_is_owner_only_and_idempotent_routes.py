from __future__ import annotations

import pytest

from tests.trials.routes.trials_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_terminate_is_owner_only_and_idempotent(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(async_session, email="owner-term@test.com")
    outsider = await create_talent_partner(
        async_session, email="outsider-term@test.com"
    )
    created = await _create_trial_via_api(
        async_client, async_session, auth_header_factory(owner)
    )
    sim_id = created["id"]

    forbidden = await async_client.post(
        f"/api/trials/{sim_id}/terminate",
        headers=auth_header_factory(outsider),
        json={"confirm": True},
    )
    assert forbidden.status_code == 403

    first = await async_client.post(
        f"/api/trials/{sim_id}/terminate",
        headers=auth_header_factory(owner),
        json={"confirm": True, "reason": "regenerate"},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["status"] == "terminated"
    assert first_body["terminatedAt"] is not None
    assert len(first_body["cleanupJobIds"]) == 1
    first_job_id = first_body["cleanupJobIds"][0]

    jobs_after_first = (
        await async_session.execute(select(Job).where(Job.job_type == "trial_cleanup"))
    ).scalars()
    matching_first = [
        job
        for job in jobs_after_first
        if isinstance(job.payload_json, dict)
        and job.payload_json.get("trialId") == sim_id
    ]
    assert len(matching_first) == 1
    assert matching_first[0].id == first_job_id
    assert matching_first[0].job_type == "trial_cleanup"
    assert matching_first[0].idempotency_key == f"trial_cleanup:{sim_id}"
    assert matching_first[0].payload_json["reason"] == "regenerate"

    second = await async_client.post(
        f"/api/trials/{sim_id}/terminate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["status"] == "terminated"
    assert second_body["terminatedAt"] == first_body["terminatedAt"]
    assert second_body["cleanupJobIds"] == first_body["cleanupJobIds"]

    jobs_after_second = (
        await async_session.execute(select(Job).where(Job.job_type == "trial_cleanup"))
    ).scalars()
    matching_second = [
        job
        for job in jobs_after_second
        if isinstance(job.payload_json, dict)
        and job.payload_json.get("trialId") == sim_id
    ]
    assert len(matching_second) == 1
    assert matching_second[0].id == first_job_id
