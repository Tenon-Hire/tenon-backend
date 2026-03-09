from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains import Job, ScenarioVersion, Simulation, Task
from app.jobs import worker
from app.jobs.handlers import scenario_generation as scenario_handler
from app.repositories.jobs.models import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
)
from tests.factories import create_recruiter


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


@pytest.fixture(autouse=True)
def _patch_scenario_handler_session_maker(async_session, monkeypatch):
    monkeypatch.setattr(
        scenario_handler, "async_session_maker", _session_maker(async_session)
    )


async def _create_simulation(async_client, headers: dict[str, str]) -> dict:
    response = await async_client.post(
        "/api/simulations",
        headers=headers,
        json={
            "title": "Scenario Generation API",
            "role": "Backend Engineer",
            "techStack": "Python, FastAPI, PostgreSQL",
            "seniority": "Mid",
            "focus": "Validate scenario generation flow",
            "templateKey": "python-fastapi",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_simulation_returns_generating_and_scenario_job_id(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="scenario-api-create@test.com"
    )
    created = await _create_simulation(async_client, auth_header_factory(recruiter))

    assert created["status"] == "generating"
    assert created["scenarioGenerationJobId"]

    simulation = await async_session.get(Simulation, created["id"])
    assert simulation is not None
    assert simulation.status == "generating"
    assert simulation.active_scenario_version_id is None

    job = await async_session.get(Job, created["scenarioGenerationJobId"])
    assert job is not None
    assert job.job_type == "scenario_generation"
    assert job.status == JOB_STATUS_QUEUED
    assert job.payload_json["simulationId"] == created["id"]


@pytest.mark.asyncio
async def test_scenario_generation_job_creates_v1_and_updates_detail_read(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="scenario-api-run@test.com")
    recruiter_email = recruiter.email
    created = await _create_simulation(async_client, auth_header_factory(recruiter))
    simulation_id = created["id"]
    job_id = created["scenarioGenerationJobId"]

    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=_session_maker(async_session),
            worker_id="scenario-api-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        refreshed_simulation = await check_session.get(Simulation, simulation_id)
        refreshed_job = await check_session.get(Job, job_id)
        scenario_v1 = (
            await check_session.execute(
                select(ScenarioVersion).where(
                    ScenarioVersion.simulation_id == simulation_id,
                    ScenarioVersion.version_index == 1,
                )
            )
        ).scalar_one()
        task_rows = (
            (
                await check_session.execute(
                    select(Task)
                    .where(Task.simulation_id == simulation_id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
    assert refreshed_simulation is not None
    assert refreshed_job is not None
    assert refreshed_simulation.status == "ready_for_review"
    assert refreshed_simulation.active_scenario_version_id is not None
    assert refreshed_job.status == JOB_STATUS_SUCCEEDED
    assert (
        refreshed_job.idempotency_key
        == f"simulation:{simulation_id}:scenario_generation"
    )

    assert scenario_v1.storyline_md
    assert scenario_v1.task_prompts_json
    assert isinstance(scenario_v1.rubric_json, dict)
    assert scenario_v1.model_name == "template_catalog_fallback"
    assert scenario_v1.prompt_version == "scenario-generation-v1"

    assert len(task_rows) == 5
    assert all((task.description or "").strip() for task in task_rows)
    assert all(task.max_score is not None for task in task_rows)

    detail_response = await async_client.get(
        f"/api/simulations/{simulation_id}",
        headers=auth_header_factory(recruiter),
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["status"] == "ready_for_review"
    assert detail["scenario"] is not None
    assert detail["scenario"]["id"] == scenario_v1.id
    assert detail["scenario"]["versionIndex"] == 1
    assert detail["scenario"]["status"] == scenario_v1.status
    assert detail["scenario"]["storylineMd"] == scenario_v1.storyline_md
    assert detail["scenario"]["taskPromptsJson"] == scenario_v1.task_prompts_json
    assert detail["scenario"]["rubricJson"] == scenario_v1.rubric_json
    assert detail["scenario"]["modelName"] == scenario_v1.model_name
    assert detail["scenario"]["modelVersion"] == scenario_v1.model_version
    assert detail["scenario"]["promptVersion"] == scenario_v1.prompt_version
    assert detail["scenario"]["rubricVersion"] == scenario_v1.rubric_version

    prompts_by_day = {
        int(prompt["dayIndex"]): prompt
        for prompt in detail["scenario"]["taskPromptsJson"]
    }
    tasks_by_day = {int(task["dayIndex"]): task for task in detail["tasks"]}
    assert sorted(prompts_by_day) == [1, 2, 3, 4, 5]
    assert sorted(tasks_by_day) == [1, 2, 3, 4, 5]

    rubric_day_weights = detail["scenario"]["rubricJson"]["dayWeights"]
    for day_index in [1, 2, 3, 4, 5]:
        assert (
            tasks_by_day[day_index]["description"]
            == prompts_by_day[day_index]["description"]
        )
        assert tasks_by_day[day_index]["maxScore"] == rubric_day_weights[str(day_index)]

    async_session.expire_all()
    job_status_response = await async_client.get(
        f"/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer recruiter:{recruiter_email}"},
    )
    assert job_status_response.status_code == 200, job_status_response.text
    job_status = job_status_response.json()
    assert job_status["jobType"] == "scenario_generation"
    assert job_status["status"] == "completed"


@pytest.mark.asyncio
async def test_scenario_generation_failure_marks_job_failed_and_keeps_generating(
    async_client, async_session, auth_header_factory, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="scenario-api-failure@test.com"
    )
    recruiter_email = recruiter.email
    created = await _create_simulation(async_client, auth_header_factory(recruiter))
    simulation_id = created["id"]
    job_id = created["scenarioGenerationJobId"]

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        job = await check_session.get(Job, job_id)
        assert job is not None
        job.max_attempts = 1
        await check_session.commit()

    def _explode(*, role: str, tech_stack: str, template_key: str):
        raise RuntimeError("forced scenario generation failure")

    monkeypatch.setattr(scenario_handler, "generate_scenario_payload", _explode)

    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=_session_maker(async_session),
            worker_id="scenario-api-failure-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True

    async with session_maker() as check_session:
        refreshed_simulation = await check_session.get(Simulation, simulation_id)
        refreshed_job = await check_session.get(Job, job_id)
    assert refreshed_simulation is not None
    assert refreshed_job is not None
    assert refreshed_simulation.status == "generating"
    assert refreshed_simulation.active_scenario_version_id is None
    assert refreshed_job.status == JOB_STATUS_DEAD_LETTER

    async_session.expire_all()
    job_status_response = await async_client.get(
        f"/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer recruiter:{recruiter_email}"},
    )
    assert job_status_response.status_code == 200, job_status_response.text
    job_status = job_status_response.json()
    assert job_status["jobType"] == "scenario_generation"
    assert job_status["status"] == "failed"
    assert "forced scenario generation failure" in (job_status["error"] or "")
