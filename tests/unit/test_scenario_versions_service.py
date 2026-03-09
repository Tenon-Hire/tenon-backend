from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.errors import ApiError
from app.domains import Job, ScenarioVersion, Simulation, Task
from app.services.simulations import scenario_versions as scenario_service
from tests.factories import create_recruiter, create_simulation


async def _create_bare_simulation(async_session, recruiter):
    sim = Simulation(
        company_id=recruiter.company_id,
        title="Scenario Service Sim",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="mid",
        focus="Scenario focus",
        scenario_template="default-5day-node-postgres",
        created_by=recruiter.id,
        template_key="python-fastapi",
        status="generating",
        generating_at=datetime.now(UTC),
    )
    async_session.add(sim)
    await async_session.flush()

    day2 = Task(
        simulation_id=sim.id,
        day_index=2,
        type="code",
        title="Day 2",
        description="Code prompt",
    )
    day1 = Task(
        simulation_id=sim.id,
        day_index=1,
        type="design",
        title="Day 1",
        description="Design prompt",
    )
    async_session.add_all([day2, day1])
    await async_session.flush()
    return sim, [day2, day1]


@pytest.mark.asyncio
async def test_create_initial_scenario_version_sets_active_and_payload(async_session):
    recruiter = await create_recruiter(async_session, email="scenario-init@test.com")
    sim, tasks = await _create_bare_simulation(async_session, recruiter)

    scenario = await scenario_service.create_initial_scenario_version(
        async_session, simulation=sim, tasks=tasks
    )

    assert scenario.version_index == 1
    assert scenario.status == "ready"
    assert sim.active_scenario_version_id == scenario.id
    assert scenario.task_prompts_json[0]["dayIndex"] == 1
    assert scenario.task_prompts_json[1]["dayIndex"] == 2


def test_ensure_scenario_version_mutable_respects_locked_state():
    unlocked = ScenarioVersion(
        simulation_id=1,
        version_index=1,
        status="ready",
        storyline_md="x",
        task_prompts_json=[],
        rubric_json={},
        focus_notes="",
        template_key="python-fastapi",
        tech_stack="Python",
        seniority="mid",
    )
    scenario_service.ensure_scenario_version_mutable(unlocked)

    locked = ScenarioVersion(
        simulation_id=1,
        version_index=1,
        status="locked",
        storyline_md="x",
        task_prompts_json=[],
        rubric_json={},
        focus_notes="",
        template_key="python-fastapi",
        tech_stack="Python",
        seniority="mid",
    )
    with pytest.raises(ApiError) as excinfo:
        scenario_service.ensure_scenario_version_mutable(locked)
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_LOCKED"


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_success(async_session):
    recruiter = await create_recruiter(async_session, email="scenario-lock-ok@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    now = datetime.now(UTC).replace(microsecond=0)

    locked = await scenario_service.lock_active_scenario_for_invites(
        async_session, simulation_id=sim.id, now=now
    )

    assert locked.status == "locked"
    assert locked.locked_at == now


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_not_found(async_session):
    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.lock_active_scenario_for_invites(
            async_session, simulation_id=999999
        )
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_requires_active_version(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-lock-missing-active@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    sim.status = "generating"
    sim.active_scenario_version_id = None
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.lock_active_scenario_for_invites(
            async_session, simulation_id=sim.id
        )
    assert excinfo.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_rejects_non_ready(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-lock-nonready@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "draft"
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.lock_active_scenario_for_invites(
            async_session, simulation_id=sim.id
        )
    assert excinfo.value.error_code == "SCENARIO_NOT_READY"


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_rejects_mismatched_active(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="scenario-lock-mismatch@test.com"
    )
    sim1, _tasks1 = await create_simulation(async_session, created_by=recruiter)
    sim2, _tasks2 = await create_simulation(async_session, created_by=recruiter)
    sim1.active_scenario_version_id = sim2.active_scenario_version_id
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.lock_active_scenario_for_invites(
            async_session, simulation_id=sim1.id
        )
    assert excinfo.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_is_idempotent_for_locked(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-lock-idempotent@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "locked"
    active.locked_at = datetime.now(UTC)
    await async_session.commit()

    locked = await scenario_service.lock_active_scenario_for_invites(
        async_session, simulation_id=sim.id
    )
    assert locked.id == active.id
    assert locked.status == "locked"


@pytest.mark.asyncio
async def test_regenerate_active_scenario_version_creates_incremented_row(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-ok@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)

    previous_active = sim.active_scenario_version_id
    (
        updated_sim,
        regenerated,
    ) = await scenario_service.regenerate_active_scenario_version(
        async_session,
        simulation_id=sim.id,
        actor_user_id=recruiter.id,
    )

    assert regenerated.version_index == 2
    assert regenerated.id != previous_active
    assert regenerated.status == "generating"
    assert updated_sim.active_scenario_version_id == previous_active
    assert updated_sim.pending_scenario_version_id == regenerated.id
    assert updated_sim.status == "ready_for_review"

    versions = (
        (
            await async_session.execute(
                select(ScenarioVersion)
                .where(ScenarioVersion.simulation_id == sim.id)
                .order_by(ScenarioVersion.version_index.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [version.version_index for version in versions] == [1, 2]
    assert versions[0].id == previous_active
    assert versions[1].id == regenerated.id


@pytest.mark.asyncio
async def test_request_scenario_regeneration_enqueues_targeted_job(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-job@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    previous_active = sim.active_scenario_version_id

    (
        updated_sim,
        regenerated,
        scenario_job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        simulation_id=sim.id,
        actor_user_id=recruiter.id,
    )

    assert regenerated.status == "generating"
    assert regenerated.version_index == 2
    assert updated_sim.active_scenario_version_id == previous_active
    assert updated_sim.pending_scenario_version_id == regenerated.id
    assert scenario_job.job_type == "scenario_generation"
    assert scenario_job.payload_json["simulationId"] == sim.id
    assert scenario_job.payload_json["scenarioVersionId"] == regenerated.id

    persisted = await async_session.get(Job, scenario_job.id)
    assert persisted is not None
    assert (
        persisted.idempotency_key
        == f"scenario_version:{regenerated.id}:scenario_generation"
    )

    with pytest.raises(ApiError) as duplicate_exc:
        await scenario_service.request_scenario_regeneration(
            async_session,
            simulation_id=sim.id,
            actor_user_id=recruiter.id,
        )
    assert duplicate_exc.value.status_code == 409
    assert duplicate_exc.value.error_code == "SCENARIO_REGENERATION_PENDING"


@pytest.mark.asyncio
async def test_regenerate_active_scenario_version_owner_and_active_guards(
    async_session,
):
    owner = await create_recruiter(async_session, email="scenario-regen-owner@test.com")
    outsider = await create_recruiter(
        async_session, email="scenario-regen-outsider@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=owner)

    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.regenerate_active_scenario_version(
            async_session,
            simulation_id=sim.id,
            actor_user_id=outsider.id,
        )
    assert excinfo.value.status_code == 403

    sim.status = "generating"
    sim.active_scenario_version_id = None
    await async_session.commit()
    with pytest.raises(ApiError) as missing_exc:
        await scenario_service.regenerate_active_scenario_version(
            async_session,
            simulation_id=sim.id,
            actor_user_id=owner.id,
        )
    assert missing_exc.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"


@pytest.mark.asyncio
async def test_regenerate_active_scenario_version_rejects_mismatched_active(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-mismatch@test.com"
    )
    sim1, _tasks1 = await create_simulation(async_session, created_by=recruiter)
    sim2, _tasks2 = await create_simulation(async_session, created_by=recruiter)
    sim1.active_scenario_version_id = sim2.active_scenario_version_id
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.regenerate_active_scenario_version(
            async_session,
            simulation_id=sim1.id,
            actor_user_id=recruiter.id,
        )
    assert excinfo.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"


@pytest.mark.asyncio
async def test_approve_scenario_version_promotes_pending_to_active(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-approve-ok@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    previous_active = sim.active_scenario_version_id
    (
        _updated_sim,
        regenerated,
        _job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        simulation_id=sim.id,
        actor_user_id=recruiter.id,
    )
    regenerated.status = "ready"
    await async_session.commit()

    approved_sim, approved_version = await scenario_service.approve_scenario_version(
        async_session,
        simulation_id=sim.id,
        scenario_version_id=regenerated.id,
        actor_user_id=recruiter.id,
    )

    assert approved_version.id == regenerated.id
    assert approved_sim.pending_scenario_version_id is None
    assert approved_sim.active_scenario_version_id == regenerated.id
    assert approved_sim.active_scenario_version_id != previous_active
    assert approved_sim.status == "active_inviting"

    first_session_active = await async_session.get(ScenarioVersion, previous_active)
    assert first_session_active is not None


@pytest.mark.asyncio
async def test_approve_scenario_version_guards(async_session):
    owner = await create_recruiter(
        async_session, email="scenario-approve-owner@test.com"
    )
    outsider = await create_recruiter(
        async_session, email="scenario-approve-outsider@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=owner)
    (
        _updated_sim,
        regenerated,
        _job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        simulation_id=sim.id,
        actor_user_id=owner.id,
    )

    with pytest.raises(HTTPException) as forbidden_exc:
        await scenario_service.approve_scenario_version(
            async_session,
            simulation_id=sim.id,
            scenario_version_id=regenerated.id,
            actor_user_id=outsider.id,
        )
    assert forbidden_exc.value.status_code == 403

    with pytest.raises(ApiError) as not_ready_exc:
        await scenario_service.approve_scenario_version(
            async_session,
            simulation_id=sim.id,
            scenario_version_id=regenerated.id,
            actor_user_id=owner.id,
        )
    assert not_ready_exc.value.status_code == 409
    assert not_ready_exc.value.error_code == "SCENARIO_NOT_READY"

    regenerated.status = "ready"
    await async_session.commit()

    with pytest.raises(ApiError) as mismatch_exc:
        await scenario_service.approve_scenario_version(
            async_session,
            simulation_id=sim.id,
            scenario_version_id=sim.active_scenario_version_id,
            actor_user_id=owner.id,
        )
    assert mismatch_exc.value.status_code == 409
    assert mismatch_exc.value.error_code == "SCENARIO_VERSION_NOT_PENDING"


@pytest.mark.asyncio
async def test_request_scenario_regeneration_missing_simulation_returns_404(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-missing@test.com"
    )
    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.request_scenario_regeneration(
            async_session,
            simulation_id=999999,
            actor_user_id=recruiter.id,
        )
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_approve_scenario_version_without_pending_state_branches(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-approve-nopending@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    active_id = sim.active_scenario_version_id
    assert active_id is not None

    sim.status = "ready_for_review"
    await async_session.flush()

    approved_sim, approved_version = await scenario_service.approve_scenario_version(
        async_session,
        simulation_id=sim.id,
        scenario_version_id=active_id,
        actor_user_id=recruiter.id,
    )
    assert approved_sim.status == "active_inviting"
    assert approved_version.id == active_id

    non_active = ScenarioVersion(
        simulation_id=sim.id,
        version_index=2,
        status="ready",
        storyline_md="# v2",
        task_prompts_json=[],
        rubric_json={},
        focus_notes=sim.focus,
        template_key=sim.template_key,
        tech_stack=sim.tech_stack,
        seniority=sim.seniority,
    )
    async_session.add(non_active)
    await async_session.commit()

    with pytest.raises(ApiError) as not_pending_exc:
        await scenario_service.approve_scenario_version(
            async_session,
            simulation_id=sim.id,
            scenario_version_id=non_active.id,
            actor_user_id=recruiter.id,
        )
    assert not_pending_exc.value.status_code == 409
    assert not_pending_exc.value.error_code == "SCENARIO_APPROVAL_NOT_PENDING"


@pytest.mark.asyncio
async def test_approve_scenario_version_not_found_returns_404(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-approve-missing@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)

    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.approve_scenario_version(
            async_session,
            simulation_id=sim.id,
            scenario_version_id=999999,
            actor_user_id=recruiter.id,
        )
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_update_active_scenario_version_success_and_validation(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-update-success@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)

    updated = await scenario_service.update_active_scenario_version(
        async_session,
        simulation_id=sim.id,
        actor_user_id=recruiter.id,
        updates={
            "storyline_md": "## Updated",
            "task_prompts_json": [{"dayIndex": 1}],
            "rubric_json": {"summary": "rubric"},
            "focus_notes": "Updated focus",
            "status": "draft",
        },
    )
    assert updated.storyline_md == "## Updated"
    assert updated.task_prompts_json == [{"dayIndex": 1}]
    assert updated.rubric_json == {"summary": "rubric"}
    assert updated.focus_notes == "Updated focus"
    assert updated.status == "draft"

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.update_active_scenario_version(
            async_session,
            simulation_id=sim.id,
            actor_user_id=recruiter.id,
            updates={"status": "invalid"},
        )
    assert excinfo.value.status_code == 422
    assert excinfo.value.error_code == "SCENARIO_STATUS_INVALID"


@pytest.mark.asyncio
async def test_update_active_scenario_version_locked_and_missing_guards(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-update-guards@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "locked"
    await async_session.commit()

    with pytest.raises(ApiError) as locked_exc:
        await scenario_service.update_active_scenario_version(
            async_session,
            simulation_id=sim.id,
            actor_user_id=recruiter.id,
            updates={"focus_notes": "x"},
        )
    assert locked_exc.value.error_code == "SCENARIO_LOCKED"

    sim.status = "generating"
    sim.active_scenario_version_id = None
    await async_session.commit()
    with pytest.raises(ApiError) as missing_exc:
        await scenario_service.update_active_scenario_version(
            async_session,
            simulation_id=sim.id,
            actor_user_id=recruiter.id,
            updates={"focus_notes": "x"},
        )
    assert missing_exc.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"


@pytest.mark.asyncio
async def test_update_active_scenario_version_rejects_mismatched_active(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-update-mismatch@test.com"
    )
    sim1, _tasks1 = await create_simulation(async_session, created_by=recruiter)
    sim2, _tasks2 = await create_simulation(async_session, created_by=recruiter)
    sim1.active_scenario_version_id = sim2.active_scenario_version_id
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.update_active_scenario_version(
            async_session,
            simulation_id=sim1.id,
            actor_user_id=recruiter.id,
            updates={"focus_notes": "x"},
        )
    assert excinfo.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"
