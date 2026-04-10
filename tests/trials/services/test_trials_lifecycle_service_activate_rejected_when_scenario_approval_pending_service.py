from __future__ import annotations

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


@pytest.mark.asyncio
async def test_activate_rejected_when_scenario_approval_pending(async_session):
    company = Company(name="Activate Pending Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-activate-pending@test.com",
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    trial = Trial(
        company_id=company.id,
        title="Pending Approval",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Reject lifecycle activate while pending scenario approval",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.TRIAL_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(trial)
    await async_session.flush()
    await _attach_active_scenario(async_session, trial)
    pending = ScenarioVersion(
        trial_id=trial.id,
        version_index=2,
        status="generating",
        storyline_md="# pending",
        task_prompts_json=[],
        rubric_json={},
        focus_notes=trial.focus or "",
        template_key=trial.template_key,
        tech_stack=trial.tech_stack,
        seniority=trial.seniority,
    )
    async_session.add(pending)
    await async_session.flush()
    trial.status = sim_service.TRIAL_STATUS_READY_FOR_REVIEW
    trial.ready_for_review_at = datetime.now(UTC)
    trial.pending_scenario_version_id = pending.id
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await sim_service.activate_trial(
            async_session,
            trial_id=trial.id,
            actor_user_id=owner.id,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_APPROVAL_PENDING"
