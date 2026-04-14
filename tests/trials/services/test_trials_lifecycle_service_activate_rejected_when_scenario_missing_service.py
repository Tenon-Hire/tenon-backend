from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


@pytest.mark.asyncio
async def test_activate_rejected_when_scenario_missing(async_session):
    company = Company(name="Activate Missing Guard Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-activate-missing@test.com",
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    trial = Trial(
        company_id=company.id,
        title="Missing Scenario",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Reject lifecycle activate without a locked scenario",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.TRIAL_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(trial)
    await async_session.flush()
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await sim_service.activate_trial(
            async_session,
            trial_id=trial.id,
            actor_user_id=owner.id,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_LOCK_REQUIRED"


@pytest.mark.asyncio
async def test_prepare_active_scenario_bundle_on_activation_returns_none_when_missing(
    monkeypatch,
):
    async def _missing_active_scenario_version(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        lifecycle_service,
        "get_active_scenario_version",
        _missing_active_scenario_version,
    )

    result = await lifecycle_service._prepare_active_scenario_bundle_on_activation(
        object(), trial=SimpleNamespace(id=1)
    )

    assert result is None
