from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_trial_fallback_updates_future_invites_only(
    async_client,
    async_session,
    monkeypatch,
    auth_header_factory,
):
    admin_email = "ops-fallback@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    talent_partner = await create_talent_partner(
        async_session, email="owner-fallback@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    first_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="first-fallback@example.com",
    )

    scenario_v1 = await async_session.get(
        ScenarioVersion, trial.active_scenario_version_id
    )
    assert scenario_v1 is not None
    scenario_v2 = ScenarioVersion(
        trial_id=trial.id,
        version_index=2,
        status="ready",
        storyline_md=f"{scenario_v1.storyline_md}\n\nFallback variant",
        task_prompts_json=scenario_v1.task_prompts_json,
        rubric_json=scenario_v1.rubric_json,
        focus_notes=scenario_v1.focus_notes,
        template_key=scenario_v1.template_key,
        tech_stack=scenario_v1.tech_stack,
        seniority=scenario_v1.seniority,
    )
    async_session.add(scenario_v2)
    await async_session.commit()

    fallback_response = await async_client.post(
        f"/api/admin/trials/{trial.id}/scenario/use_fallback",
        json={
            "scenarioVersionId": scenario_v2.id,
            "applyTo": "future_invites_only",
            "reason": "Swap to known-good fallback for demo",
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert fallback_response.status_code == 200, fallback_response.text
    fallback_payload = fallback_response.json()
    assert fallback_payload["trialId"] == trial.id
    assert fallback_payload["activeScenarioVersionId"] == scenario_v2.id
    assert fallback_payload["applyTo"] == "future_invites_only"
    assert isinstance(fallback_payload["auditId"], str)

    refreshed_trial = await async_session.get(Trial, trial.id)
    assert refreshed_trial is not None
    assert refreshed_trial.active_scenario_version_id == scenario_v2.id

    refreshed_first = await async_session.get(type(first_session), first_session.id)
    assert refreshed_first is not None
    assert refreshed_first.scenario_version_id == scenario_v1.id

    invite_response = await async_client.post(
        f"/api/trials/{trial.id}/invite",
        headers=auth_header_factory(talent_partner),
        json={
            "candidateName": "Second Candidate",
            "inviteEmail": "second-fallback@example.com",
        },
    )
    assert invite_response.status_code == 200, invite_response.text
    second_session_id = invite_response.json()["candidateSessionId"]
    second_session = await async_session.get(type(first_session), second_session_id)
    assert second_session is not None
    assert second_session.scenario_version_id == scenario_v2.id

    noop_response = await async_client.post(
        f"/api/admin/trials/{trial.id}/scenario/use_fallback",
        json={
            "scenarioVersionId": scenario_v2.id,
            "applyTo": "future_invites_only",
            "reason": "Repeat fallback no-op",
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert noop_response.status_code == 200, noop_response.text
    assert noop_response.json()["activeScenarioVersionId"] == scenario_v2.id

    audit = await async_session.get(AdminActionAudit, fallback_payload["auditId"])
    assert audit is not None
    assert audit.action == "trial_use_fallback"
    assert audit.target_type == "trial"
    assert audit.target_id == str(trial.id)
