from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains import ScenarioVersion, Simulation, Task
from app.jobs import worker
from app.jobs.handlers import scenario_generation as scenario_handler
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import JOB_STATUS_DEAD_LETTER
from app.repositories.scenario_versions.models import SCENARIO_VERSION_STATUS_READY
from app.services.simulations.creation import create_simulation_with_tasks
from tests.factories import create_recruiter


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


def _simulation_payload() -> object:
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


def test_parse_positive_int_variants() -> None:
    assert scenario_handler._parse_positive_int(True) is None
    assert scenario_handler._parse_positive_int("12") == 12
    assert scenario_handler._parse_positive_int("0") is None
    assert scenario_handler._parse_positive_int("not-a-number") is None


@pytest.mark.asyncio
async def test_scenario_generation_handler_skips_invalid_payload() -> None:
    result = await scenario_handler.handle_scenario_generation({"simulationId": False})
    assert result == {"status": "skipped_invalid_payload", "simulationId": None}


@pytest.mark.asyncio
async def test_scenario_generation_handler_returns_not_found_for_missing_simulation() -> (
    None
):
    result = await scenario_handler.handle_scenario_generation({"simulationId": 999999})
    assert result == {"status": "simulation_not_found", "simulationId": 999999}


@pytest.mark.asyncio
async def test_scenario_generation_handler_is_idempotent_for_existing_v1(async_session):
    recruiter = await create_recruiter(
        async_session, email="idempotent-scenario@test.com"
    )
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )

    first = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    second = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert first["status"] == "completed"
    assert second["status"] == "completed"

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        versions = (
            (
                await check_session.execute(
                    select(ScenarioVersion)
                    .where(ScenarioVersion.simulation_id == sim.id)
                    .order_by(ScenarioVersion.version_index.asc())
                )
            )
            .scalars()
            .all()
        )
        refreshed_sim = await check_session.get(Simulation, sim.id)
    assert len(versions) == 1
    assert versions[0].version_index == 1
    assert refreshed_sim is not None
    assert refreshed_sim.status == "ready_for_review"
    assert refreshed_sim.active_scenario_version_id == versions[0].id


@pytest.mark.asyncio
async def test_scenario_generation_handler_skips_non_mutable_simulation(async_session):
    recruiter = await create_recruiter(async_session, email="non-mutable-sim@test.com")
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )
    completed = await scenario_handler.handle_scenario_generation(
        {"simulationId": sim.id}
    )
    assert completed["status"] == "completed"
    sim.status = "terminated"
    await async_session.commit()

    result = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert result == {
        "status": "skipped_non_mutable_simulation",
        "simulationId": sim.id,
        "simulationStatus": "terminated",
    }


@pytest.mark.asyncio
async def test_scenario_generation_handler_skips_unexpected_status(async_session):
    recruiter = await create_recruiter(
        async_session, email="unexpected-status-sim@test.com"
    )
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )
    sim.status = "draft"
    await async_session.commit()

    result = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert result == {
        "status": "skipped_unexpected_status",
        "simulationId": sim.id,
        "simulationStatus": "draft",
    }


@pytest.mark.asyncio
async def test_scenario_generation_handler_reuses_existing_v1_while_generating(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="existing-v1-generating@test.com"
    )
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )

    existing_v1 = ScenarioVersion(
        simulation_id=sim.id,
        version_index=1,
        status=SCENARIO_VERSION_STATUS_READY,
        storyline_md="stale storyline",
        task_prompts_json=[],
        rubric_json={},
        focus_notes=sim.focus or "",
        template_key=sim.template_key,
        tech_stack=sim.tech_stack,
        seniority=sim.seniority,
    )
    async_session.add(existing_v1)
    await async_session.commit()

    first = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert first["status"] == "completed"
    assert first["scenarioVersionId"] == existing_v1.id

    first_task_snapshot = [
        (task.day_index, task.title, task.description, task.max_score)
        for task in (
            (
                await async_session.execute(
                    select(Task)
                    .where(Task.simulation_id == sim.id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
    ]

    second = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert second["status"] == "completed"
    assert second["scenarioVersionId"] == existing_v1.id

    second_task_snapshot = [
        (task.day_index, task.title, task.description, task.max_score)
        for task in (
            (
                await async_session.execute(
                    select(Task)
                    .where(Task.simulation_id == sim.id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
    ]
    assert second_task_snapshot == first_task_snapshot

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        versions = (
            (
                await check_session.execute(
                    select(ScenarioVersion)
                    .where(ScenarioVersion.simulation_id == sim.id)
                    .order_by(ScenarioVersion.version_index.asc())
                )
            )
            .scalars()
            .all()
        )
        refreshed_sim = await check_session.get(Simulation, sim.id)
    assert len(versions) == 1
    assert versions[0].id == existing_v1.id

    assert refreshed_sim is not None
    assert refreshed_sim.status == "ready_for_review"
    assert refreshed_sim.active_scenario_version_id == existing_v1.id


@pytest.mark.asyncio
async def test_scenario_generation_handler_raises_when_seeded_tasks_missing(
    async_session,
):
    recruiter = await create_recruiter(async_session, email="missing-tasks@test.com")
    sim, tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )
    for task in tasks:
        await async_session.delete(task)
    await async_session.commit()

    with pytest.raises(RuntimeError, match="scenario_generation_missing_seeded_tasks"):
        await scenario_handler.handle_scenario_generation({"simulationId": sim.id})


@pytest.mark.asyncio
async def test_scenario_generation_worker_failure_preserves_generating_state(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(async_session, email="fail-scenario@test.com")
    sim, _tasks, job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )
    job.max_attempts = 1
    await async_session.commit()

    def _explode(*, role: str, tech_stack: str, template_key: str):
        raise RuntimeError("forced scenario generation failure")

    monkeypatch.setattr(scenario_handler, "generate_scenario_payload", _explode)

    worker.register_builtin_handlers()
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="scenario-failure-worker",
        now=datetime.now(UTC),
    )
    assert handled is True

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        refreshed_sim = await check_session.get(Simulation, sim.id)
        refreshed_job = await jobs_repo.get_by_id(check_session, job.id)
    assert refreshed_sim is not None
    assert refreshed_job is not None

    assert refreshed_sim.status == "generating"
    assert refreshed_sim.active_scenario_version_id is None
    assert refreshed_job.status == JOB_STATUS_DEAD_LETTER
    assert "forced scenario generation failure" in (refreshed_job.last_error or "")

    versions = (
        (
            await async_session.execute(
                select(ScenarioVersion).where(ScenarioVersion.simulation_id == sim.id)
            )
        )
        .scalars()
        .all()
    )
    assert versions == []
