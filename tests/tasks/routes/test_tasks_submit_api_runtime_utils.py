from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.shared.jobs import worker


async def create_simulation(async_client, async_session, recruiter_email: str) -> dict:
    resp = await async_client.post(
        "/api/simulations",
        headers={"x-dev-user-email": recruiter_email},
        json={
            "title": "Backend Node Simulation",
            "role": "Backend Engineer",
            "techStack": "Node.js, PostgreSQL",
            "seniority": "Mid",
            "focus": "Build new API feature and debug an issue",
        },
    )
    assert resp.status_code == 201, resp.text
    simulation = resp.json()
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
    activate = await async_client.post(
        f"/api/simulations/{simulation['id']}/activate",
        headers={"x-dev-user-email": recruiter_email},
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text
    return simulation


__all__ = [name for name in globals() if not name.startswith("__")]
