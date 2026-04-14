from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.shared.database.shared_database_models_model import Trial
from app.shared.jobs import worker
from app.shared.jobs.handlers import scenario_generation as scenario_handler
from tests.trials.routes.trials_lifecycle_api_utils import *
from tests.trials.routes.trials_scenario_generation_flow_api_utils import (
    session_maker,
)


@pytest.mark.asyncio
async def test_activate_rejects_unlocked_scenario(
    async_client, async_session, auth_header_factory, monkeypatch
):
    owner = await create_talent_partner(async_session, email="owner-unlocked@test.com")
    monkeypatched_session_maker = session_maker(async_session)
    monkeypatch.setattr(
        scenario_handler, "async_session_maker", monkeypatched_session_maker
    )
    response = await async_client.post(
        "/api/trials",
        headers=auth_header_factory(owner),
        json={
            "title": "Unlocked Guard",
            "role": "Backend Engineer",
            "techStack": "Python, FastAPI",
            "seniority": "Mid",
            "focus": "Verify activation is blocked before approval",
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    trial_id = created["id"]

    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=monkeypatched_session_maker,
            worker_id="activate-unlocked-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True
    trial = await async_session.get(Trial, trial_id)
    assert trial is not None
    assert trial.active_scenario_version_id is not None

    response = await async_client.post(
        f"/api/trials/{trial_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["errorCode"] == "SCENARIO_LOCK_REQUIRED"
