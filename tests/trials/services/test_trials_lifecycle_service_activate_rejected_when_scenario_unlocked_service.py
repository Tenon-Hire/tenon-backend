from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


@pytest.mark.asyncio
async def test_activate_rejected_when_scenario_unlocked(async_session):
    company = Company(name="Activate Locked Guard Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-activate-locked@test.com",
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    trial = Trial(
        company_id=company.id,
        title="Unlocked Scenario",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Reject lifecycle activate unless scenario is locked",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.TRIAL_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(trial)
    await async_session.flush()
    await _attach_active_scenario(async_session, trial)
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await sim_service.activate_trial(
            async_session,
            trial_id=trial.id,
            actor_user_id=owner.id,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_LOCK_REQUIRED"
