from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.ai import AIPolicySnapshotError, build_ai_policy_snapshot
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


@pytest.mark.asyncio
async def test_activate_rejected_when_scenario_snapshot_invalid(async_session):
    company = Company(name="Activate Snapshot Guard Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-activate-snapshot@test.com",
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    trial = Trial(
        company_id=company.id,
        title="Invalid Snapshot",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Reject lifecycle activation if snapshot is malformed",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.TRIAL_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(trial)
    await async_session.flush()
    await _attach_active_scenario(async_session, trial)
    active = await async_session.get(ScenarioVersion, trial.active_scenario_version_id)
    assert active is not None
    active.ai_policy_snapshot_json = build_ai_policy_snapshot(
        trial=SimpleNamespace(
            ai_notice_version="mvp1",
            ai_notice_text="AI assistance may be used for evaluation support.",
            ai_eval_enabled_by_day={
                "1": True,
                "2": True,
                "3": True,
                "4": True,
                "5": True,
            },
        )
    )
    active.ai_policy_snapshot_json["agents"]["codespace"] = {
        "key": "codespace",
        "promptVersion": "legacy",
        "rubricVersion": "legacy",
        "runtime": {
            "runtimeMode": "test",
            "provider": "openai",
            "model": "gpt-4.1",
        },
    }
    active.status = "locked"
    active.locked_at = datetime.now(UTC)
    await async_session.flush()
    await async_session.commit()

    with pytest.raises(
        AIPolicySnapshotError,
        match="scenario_version_ai_policy_snapshot_agent_contract_mismatch",
    ):
        await sim_service.activate_trial(
            async_session,
            trial_id=trial.id,
            actor_user_id=owner.id,
        )
