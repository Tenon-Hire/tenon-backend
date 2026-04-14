from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.shared.jobs import worker
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


async def create_trial(async_client, async_session, talent_partner_email: str) -> dict:
    resp = await async_client.post(
        "/api/trials",
        headers={"x-dev-user-email": talent_partner_email},
        json={
            "title": "Backend Node Trial",
            "role": "Backend Engineer",
            "techStack": "Node.js, PostgreSQL",
            "seniority": "Mid",
            "focus": "Build new API feature and debug an issue",
        },
    )
    assert resp.status_code == 201, resp.text
    trial = resp.json()
    session_maker = async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="task-submit-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True
    await _approve_trial(
        async_client,
        sim_id=trial["id"],
        headers={"x-dev-user-email": talent_partner_email},
    )
    activate = await async_client.post(
        f"/api/trials/{trial['id']}/activate",
        headers={"x-dev-user-email": talent_partner_email},
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text
    return trial


__all__ = [name for name in globals() if not name.startswith("__")]
