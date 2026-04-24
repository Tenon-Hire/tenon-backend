"""Application module for trials services trials scenario versions create service workflows."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import (
    build_ai_policy_snapshot,
    validate_current_ai_policy_snapshot_contract,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_rubric_snapshots_service import (
    materialize_scenario_version_rubric_snapshots,
)
from app.shared.database.shared_database_models_model import (
    Company,
    ScenarioVersion,
    Task,
    Trial,
)
from app.trials.repositories.scenario_versions import (
    trials_repositories_scenario_versions_trials_scenario_versions_repository as scenario_repo,
)
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_READY,
)
from app.trials.services.trials_services_trials_scenario_generation_story_service import (
    build_project_brief_markdown,
)
from app.trials.services.trials_services_trials_scenario_versions_defaults_service import (
    default_storyline_md,
    task_prompts_payload,
)

logger = logging.getLogger(__name__)


async def create_initial_scenario_version(
    db: AsyncSession,
    *,
    trial: Trial,
    tasks: list[Task],
) -> ScenarioVersion:
    """Create initial scenario version."""
    company_prompt_overrides_json = await db.scalar(
        select(Company.ai_prompt_overrides_json).where(Company.id == trial.company_id)
    )
    scenario_version = ScenarioVersion(
        trial_id=trial.id,
        version_index=1,
        status=SCENARIO_VERSION_STATUS_READY,
        storyline_md=default_storyline_md(trial),
        task_prompts_json=task_prompts_payload(tasks),
        project_brief_md=build_project_brief_markdown(
            role=trial.role,
            company_context=getattr(trial, "company_context", None),
            focus=trial.focus,
            preferred_language_framework=None,
        ),
        rubric_json={},
        focus_notes=trial.focus or "",
        template_key=trial.template_key,
        tech_stack=trial.tech_stack,
        seniority=trial.seniority,
        ai_policy_snapshot_json=validate_current_ai_policy_snapshot_contract(
            build_ai_policy_snapshot(
                trial=trial,
                company_prompt_overrides_json=company_prompt_overrides_json,
                trial_prompt_overrides_json=getattr(
                    trial, "ai_prompt_overrides_json", None
                ),
            )
        ),
    )
    db.add(scenario_version)
    await db.flush()
    await materialize_scenario_version_rubric_snapshots(
        db,
        scenario_version=scenario_version,
        trial=trial,
    )
    trial.active_scenario_version_id = scenario_version.id
    await db.flush()
    logger.info(
        "Scenario version created trialId=%s scenarioVersionId=%s versionIndex=%s",
        trial.id,
        scenario_version.id,
        scenario_version.version_index,
    )
    return scenario_version


async def get_active_scenario_version(
    db: AsyncSession, trial_id: int
) -> ScenarioVersion | None:
    """Return active scenario version."""
    return await scenario_repo.get_active_for_trial(db, trial_id)
