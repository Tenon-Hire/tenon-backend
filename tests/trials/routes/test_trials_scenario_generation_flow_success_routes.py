from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.ai import PROMPT_PACK_VERSION
from app.shared.database.shared_database_models_model import (
    Job,
    ScenarioVersion,
    Task,
    Trial,
)
from app.shared.jobs import worker
from app.shared.jobs.handlers import scenario_generation as scenario_handler
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_SUCCEEDED,
)
from tests.shared.factories import create_talent_partner
from tests.trials.routes.trials_scenario_generation_flow_api_utils import (
    create_trial,
    session_maker,
)


@pytest.mark.asyncio
async def test_scenario_generation_job_creates_v1_and_updates_detail_read(
    async_client, async_session, auth_header_factory, monkeypatch
):
    monkeypatch.setattr(
        scenario_handler, "async_session_maker", session_maker(async_session)
    )
    talent_partner = await create_talent_partner(
        async_session, email="scenario-api-run@test.com"
    )
    talent_partner_email = talent_partner.email
    created = await create_trial(async_client, auth_header_factory(talent_partner))
    trial_id = created["id"]
    job_id = created["scenarioGenerationJobId"]

    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker(async_session),
            worker_id="scenario-api-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True

    async with session_maker(async_session)() as check_session:
        refreshed_trial = await check_session.get(Trial, trial_id)
        refreshed_job = await check_session.get(Job, job_id)
        scenario_v1 = (
            await check_session.execute(
                select(ScenarioVersion).where(
                    ScenarioVersion.trial_id == trial_id,
                    ScenarioVersion.version_index == 1,
                )
            )
        ).scalar_one()
        task_rows = (
            (
                await check_session.execute(
                    select(Task)
                    .where(Task.trial_id == trial_id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
    assert refreshed_trial is not None and refreshed_job is not None
    assert refreshed_trial.status == "ready_for_review"
    assert refreshed_trial.active_scenario_version_id is not None
    assert refreshed_job.status == JOB_STATUS_SUCCEEDED
    assert refreshed_job.idempotency_key == f"trial:{trial_id}:scenario_generation"
    assert (
        scenario_v1.storyline_md
        and scenario_v1.task_prompts_json
        and scenario_v1.project_brief_md
        and isinstance(scenario_v1.rubric_json, dict)
    )
    assert scenario_v1.model_name == "template_catalog_fallback"
    assert scenario_v1.prompt_version == f"{PROMPT_PACK_VERSION}:prestart"
    assert len(task_rows) == 5
    assert all((task.description or "").strip() for task in task_rows)
    assert all(task.max_score is not None for task in task_rows)

    detail_response = await async_client.get(
        f"/api/trials/{trial_id}", headers=auth_header_factory(talent_partner)
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
    assert detail["scenario"]["projectBriefMd"] == scenario_v1.project_brief_md
    assert detail["scenario"]["rubricJson"] == scenario_v1.rubric_json
    assert detail["scenario"]["modelName"] == scenario_v1.model_name
    assert detail["scenario"]["modelVersion"] == scenario_v1.model_version
    assert detail["scenario"]["promptVersion"] == scenario_v1.prompt_version
    assert detail["scenario"]["rubricVersion"] == scenario_v1.rubric_version
    assert "codespaceSpecJson" not in detail["scenario"]

    prompts_by_day = {
        int(prompt["dayIndex"]): prompt
        for prompt in detail["scenario"]["taskPromptsJson"]
    }
    tasks_by_day = {int(task["dayIndex"]): task for task in detail["tasks"]}
    assert sorted(prompts_by_day) == [1, 2, 3, 4, 5]
    assert sorted(tasks_by_day) == [1, 2, 3, 4, 5]
    rubric_day_weights = detail["scenario"]["rubricJson"]["dayWeights"]
    assert prompts_by_day[3]["title"] == "Implementation Wrap-Up"
    assert "wrap-up" in prompts_by_day[3]["description"].lower()
    assert "debug" not in prompts_by_day[3]["description"].lower()
    assert "debug" not in detail["scenario"]["rubricJson"]["summary"].lower()
    for day_index in [1, 2, 3, 4, 5]:
        assert (
            tasks_by_day[day_index]["description"]
            == prompts_by_day[day_index]["description"]
        )
        assert tasks_by_day[day_index]["maxScore"] == rubric_day_weights[str(day_index)]

    async_session.expire_all()
    job_status_response = await async_client.get(
        f"/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer talent_partner:{talent_partner_email}"},
    )
    assert job_status_response.status_code == 200, job_status_response.text
    job_status = job_status_response.json()
    assert job_status["jobType"] == "scenario_generation"
    assert job_status["status"] == "completed"
