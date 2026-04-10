"""Application module for trials services trials scenario versions regeneration helpers service workflows."""

from __future__ import annotations

import copy

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    Job,
    ScenarioVersion,
    Trial,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_GENERATING,
)
from app.trials.services.trials_services_trials_scenario_generation_service import (
    SCENARIO_GENERATION_JOB_MAX_ATTEMPTS,
    SCENARIO_GENERATION_JOB_TYPE,
)
from app.trials.services.trials_services_trials_scenario_payload_builder_service import (
    build_scenario_generation_payload,
)
from app.trials.services.trials_services_trials_scenario_versions_access_service import (
    scenario_generation_idempotency_key,
)


def clone_pending_scenario(
    trial: Trial, active: ScenarioVersion, version_index: int
) -> ScenarioVersion:
    """Execute clone pending scenario."""
    return ScenarioVersion(
        trial_id=trial.id,
        version_index=version_index,
        status=SCENARIO_VERSION_STATUS_GENERATING,
        storyline_md=active.storyline_md,
        task_prompts_json=copy.deepcopy(active.task_prompts_json),
        rubric_json=copy.deepcopy(active.rubric_json),
        codespace_spec_json=copy.deepcopy(active.codespace_spec_json),
        ai_policy_snapshot_json=copy.deepcopy(active.ai_policy_snapshot_json),
        focus_notes=active.focus_notes,
        template_key=active.template_key,
        tech_stack=active.tech_stack,
        seniority=active.seniority,
        model_name=active.model_name,
        model_version=active.model_version,
        prompt_version=active.prompt_version,
        rubric_version=active.rubric_version,
        locked_at=None,
    )


async def enqueue_regeneration_job(
    db: AsyncSession, trial: Trial, regenerated: ScenarioVersion
) -> Job:
    """Enqueue regeneration job."""
    payload_json = build_scenario_generation_payload(trial)
    payload_json["scenarioVersionId"] = regenerated.id
    return await jobs_repo.create_or_get_idempotent(
        db,
        job_type=SCENARIO_GENERATION_JOB_TYPE,
        idempotency_key=scenario_generation_idempotency_key(regenerated.id),
        payload_json=payload_json,
        company_id=trial.company_id,
        correlation_id=f"trial:{trial.id}:scenario_version:{regenerated.id}",
        max_attempts=SCENARIO_GENERATION_JOB_MAX_ATTEMPTS,
        commit=False,
    )
