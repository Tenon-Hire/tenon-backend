from __future__ import annotations

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


@pytest.mark.asyncio
async def test_terminate_with_cleanup_rethrows_transition_errors(
    async_session, monkeypatch
):
    company = Company(name="Terminate Error Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-terminate-error@test.com",
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    trial = Trial(
        company_id=company.id,
        title="Terminate Error",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Transition failure",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.TRIAL_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(trial)
    await async_session.flush()
    await _attach_active_scenario(async_session, trial)
    trial.status = sim_service.TRIAL_STATUS_READY_FOR_REVIEW
    trial.ready_for_review_at = datetime.now(UTC)
    await async_session.commit()

    def _raise_transition(*_args, **_kwargs):
        raise ApiError(
            status_code=409,
            detail="invalid",
            error_code="TRIAL_INVALID_STATUS_TRANSITION",
            retryable=False,
        )

    monkeypatch.setattr(lifecycle_service, "apply_status_transition", _raise_transition)

    with pytest.raises(ApiError) as excinfo:
        await sim_service.terminate_trial_with_cleanup(
            async_session,
            trial_id=trial.id,
            actor_user_id=owner.id,
        )
    assert excinfo.value.error_code == "TRIAL_INVALID_STATUS_TRANSITION"
