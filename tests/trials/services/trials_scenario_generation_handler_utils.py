from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.database.shared_database_models_model import (
    ScenarioVersion,
    Task,
    Trial,
)
from app.shared.jobs import worker
from app.shared.jobs.handlers import scenario_generation as scenario_handler
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
)
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_GENERATING,
    SCENARIO_VERSION_STATUS_LOCKED,
    SCENARIO_VERSION_STATUS_READY,
)
from app.trials.services import create_trial_with_tasks
from tests.shared.factories import create_talent_partner


@pytest.fixture(autouse=True)
def _clear_job_handlers():
    worker.clear_handlers()
    yield
    worker.clear_handlers()


@pytest.fixture(autouse=True)
def _patch_scenario_handler_session_maker(async_session, monkeypatch):
    monkeypatch.setattr(
        scenario_handler, "async_session_maker", _session_maker(async_session)
    )


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


def _trial_payload() -> object:
    return type(
        "Payload",
        (),
        {
            "title": "Scenario Job Sim",
            "role": "Backend Engineer",
            "techStack": "Python, FastAPI",
            "seniority": "Mid",
            "focus": "Deterministic scenario generation flow",
            "templateKey": "python-fastapi",
        },
    )()


def _build_scenario_version(
    sim: Trial,
    *,
    version_index: int,
    status: str,
    storyline_md: str,
) -> ScenarioVersion:
    return ScenarioVersion(
        trial_id=sim.id,
        version_index=version_index,
        status=status,
        storyline_md=storyline_md,
        task_prompts_json=[],
        rubric_json={},
        focus_notes=sim.focus or "",
        template_key=sim.template_key,
        tech_stack=sim.tech_stack,
        seniority=sim.seniority,
    )


__all__ = [name for name in globals() if not name.startswith("__")]
