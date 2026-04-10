from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Job,
    ScenarioEditAudit,
    ScenarioVersion,
    Trial,
)
from app.shared.http.routes import trials as sim_routes
from app.shared.jobs import worker
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
)
from app.trials.schemas.trials_schemas_trials_limits_schema import (
    MAX_SCENARIO_STORYLINE_CHARS,
)
from tests.shared.factories import create_talent_partner


async def _create_trial(async_client, async_session, headers: dict[str, str]) -> int:
    response = await async_client.post(
        "/api/trials",
        headers=headers,
        json={
            "title": "Scenario Version Sim",
            "role": "Backend Engineer",
            "techStack": "Python, FastAPI",
            "seniority": "mid",
            "focus": "Scenario lock semantics",
        },
    )
    assert response.status_code == 201, response.text
    trial_id = int(response.json()["id"])
    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="scenario-versions-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True
    return trial_id


async def _run_scenario_job(async_session, *, worker_id: str) -> bool:
    session_maker = async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        return await worker.run_once(
            session_maker=session_maker,
            worker_id=worker_id,
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()


async def _invite_candidate(
    async_client, *, sim_id: int, headers, name: str, email: str
) -> int:
    response = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=headers,
        json={"candidateName": name, "inviteEmail": email},
    )
    assert response.status_code == 200, response.text
    return int(response.json()["candidateSessionId"])


async def _trial_detail(async_client, *, sim_id: int, headers) -> dict:
    response = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _active_scenario(async_session, *, sim_id: int):
    return (
        await async_session.execute(
            select(ScenarioVersion)
            .join(Trial, Trial.active_scenario_version_id == ScenarioVersion.id)
            .where(Trial.id == sim_id)
        )
    ).scalar_one()


__all__ = [name for name in globals() if not name.startswith("__")]
