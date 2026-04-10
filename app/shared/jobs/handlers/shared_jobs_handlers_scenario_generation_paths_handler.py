"""Application module for jobs handlers scenario generation paths handler workflows."""

from __future__ import annotations

from sqlalchemy import select

from app.shared.database.shared_database_models_model import ScenarioVersion
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_LOCKED,
    SCENARIO_VERSION_STATUS_READY,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_GENERATING,
)


def _apply_generated_fields(target_scenario, *, trial, generated):
    target_scenario.status = SCENARIO_VERSION_STATUS_READY
    target_scenario.storyline_md = generated.storyline_md
    target_scenario.task_prompts_json = generated.task_prompts_json
    target_scenario.rubric_json = generated.rubric_json
    target_scenario.codespace_spec_json = generated.codespace_spec_json
    target_scenario.ai_policy_snapshot_json = generated.ai_policy_snapshot_json
    target_scenario.focus_notes = trial.focus or ""
    target_scenario.template_key = trial.template_key
    target_scenario.tech_stack = trial.tech_stack
    target_scenario.seniority = trial.seniority
    target_scenario.model_name = generated.metadata.model_name
    target_scenario.model_version = generated.metadata.model_version
    target_scenario.prompt_version = generated.metadata.prompt_version
    target_scenario.rubric_version = generated.metadata.rubric_version
    target_scenario.locked_at = None


async def _apply_requested_scenario_version(
    db, *, trial, requested_scenario_version_id: int, generated
):
    target_scenario = (
        await db.execute(
            select(ScenarioVersion)
            .where(
                ScenarioVersion.id == requested_scenario_version_id,
                ScenarioVersion.trial_id == trial.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if target_scenario is None:
        return {
            "status": "scenario_version_not_found",
            "trialId": trial.id,
            "scenarioVersionId": requested_scenario_version_id,
        }, None
    if target_scenario.status == SCENARIO_VERSION_STATUS_LOCKED:
        return {
            "status": "skipped_locked_scenario_version",
            "trialId": trial.id,
            "scenarioVersionId": target_scenario.id,
        }, None
    _apply_generated_fields(target_scenario, trial=trial, generated=generated)
    return None, target_scenario.id


async def _apply_default_scenario_version(
    db, *, trial, current_status: str | None, generated
):
    existing_v1 = (
        await db.execute(
            select(ScenarioVersion)
            .where(
                ScenarioVersion.trial_id == trial.id,
                ScenarioVersion.version_index == 1,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if (
        current_status != TRIAL_STATUS_GENERATING
        and trial.active_scenario_version_id is not None
        and (existing_v1 is None or trial.active_scenario_version_id != existing_v1.id)
    ):
        return (
            {
                "status": "skipped_active_version_moved",
                "trialId": trial.id,
                "activeScenarioVersionId": trial.active_scenario_version_id,
            },
            None,
            False,
        )
    scenario_v1 = existing_v1
    created_new = scenario_v1 is None
    if scenario_v1 is None:
        scenario_v1 = ScenarioVersion(
            trial_id=trial.id,
            version_index=1,
            status=SCENARIO_VERSION_STATUS_READY,
            storyline_md="",
            task_prompts_json=[],
            rubric_json={},
            focus_notes=trial.focus or "",
            template_key=trial.template_key,
            tech_stack=trial.tech_stack,
            seniority=trial.seniority,
        )
        db.add(scenario_v1)
        await db.flush()
    _apply_generated_fields(scenario_v1, trial=trial, generated=generated)
    trial.active_scenario_version_id = scenario_v1.id
    return None, scenario_v1.id, created_new


__all__ = ["_apply_default_scenario_version", "_apply_requested_scenario_version"]
