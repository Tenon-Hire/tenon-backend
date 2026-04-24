"""Application module for jobs handlers scenario generation runtime handler workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import select

from app.ai import build_ai_policy_snapshot, resolve_scenario_generation_config
from app.evaluations.services.evaluations_services_evaluations_winoe_rubric_snapshots_service import (
    materialize_scenario_version_rubric_snapshots,
)
from app.shared.database.shared_database_models_model import (
    Company,
    ScenarioVersion,
    Task,
    Trial,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    sanitize_error,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
    TRIAL_STATUS_GENERATING,
    TRIAL_STATUS_READY_FOR_REVIEW,
    TRIAL_STATUS_TERMINATED,
)


async def handle_scenario_generation_impl(
    payload_json: dict,
    *,
    parse_positive_int,
    async_session_maker,
    normalize_trial_status,
    generate_scenario_payload,
    apply_generated_task_updates,
    apply_status_transition,
    apply_requested_scenario_version,
    apply_default_scenario_version,
    logger,
):
    """Handle scenario generation impl."""
    started = perf_counter()
    trial_id = parse_positive_int(payload_json.get("trialId"))
    if trial_id is None:
        return {"status": "skipped_invalid_payload", "trialId": None}
    requested_scenario_version_id = parse_positive_int(
        payload_json.get("scenarioVersionId")
    )
    generation_job_id = str(payload_json.get("jobId") or "")
    generation_config = resolve_scenario_generation_config()
    logger.info(
        "scenario_generation_job_started",
        extra={
            "trialId": trial_id,
            "jobId": generation_job_id,
            "runtimeMode": generation_config.runtime_mode,
            "provider": generation_config.provider,
            "model": generation_config.model,
        },
    )
    source = model_name = model_version = prompt_version = rubric_version = None
    scenario_version_id = None
    created_new = False
    async with async_session_maker() as db:
        trial = (
            await db.execute(
                select(Trial).where(Trial.id == trial_id).with_for_update()
            )
        ).scalar_one_or_none()
        if trial is None:
            return {"status": "trial_not_found", "trialId": trial_id}
        current_status = normalize_trial_status(trial.status)
        if current_status == TRIAL_STATUS_TERMINATED:
            return {
                "status": "skipped_non_mutable_trial",
                "trialId": trial_id,
                "trialStatus": current_status,
            }
        if current_status not in {
            TRIAL_STATUS_GENERATING,
            TRIAL_STATUS_READY_FOR_REVIEW,
            TRIAL_STATUS_ACTIVE_INVITING,
        }:
            return {
                "status": "skipped_unexpected_status",
                "trialId": trial_id,
                "trialStatus": current_status,
            }
        tasks = (
            (
                await db.execute(
                    select(Task)
                    .where(Task.trial_id == trial.id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
        if not tasks:
            raise RuntimeError("scenario_generation_missing_seeded_tasks")
        company_prompt_overrides_json = await db.scalar(
            select(Company.ai_prompt_overrides_json).where(
                Company.id == trial.company_id
            )
        )
        ai_policy_snapshot_json = build_ai_policy_snapshot(
            trial=trial,
            company_prompt_overrides_json=company_prompt_overrides_json,
            trial_prompt_overrides_json=getattr(
                trial, "ai_prompt_overrides_json", None
            ),
        )
        try:
            generated = generate_scenario_payload(
                role=trial.role,
                tech_stack=trial.tech_stack,
                template_key=trial.template_key,
                focus=trial.focus,
                company_context=trial.company_context,
                company_prompt_overrides_json=company_prompt_overrides_json,
                trial_prompt_overrides_json=getattr(
                    trial, "ai_prompt_overrides_json", None
                ),
                ai_policy_snapshot_json=ai_policy_snapshot_json,
            )
        except Exception as exc:
            logger.warning(
                "scenario_generation_job_failed",
                extra={
                    "trialId": trial_id,
                    "jobId": generation_job_id,
                    "runtimeMode": generation_config.runtime_mode,
                    "provider": generation_config.provider,
                    "model": generation_config.model,
                    "errorType": type(exc).__name__,
                    "errorMessage": sanitize_error(str(exc)),
                },
            )
            raise
        if requested_scenario_version_id is not None:
            early, scenario_version_id = await apply_requested_scenario_version(
                db,
                trial=trial,
                requested_scenario_version_id=requested_scenario_version_id,
                generated=generated,
            )
            if early is not None:
                return early
        else:
            (
                early,
                scenario_version_id,
                created_new,
            ) = await apply_default_scenario_version(
                db,
                trial=trial,
                current_status=current_status,
                generated=generated,
            )
            if early is not None:
                return early
        apply_generated_task_updates(
            tasks=tasks,
            task_prompts_json=generated.task_prompts_json,
            rubric_json=generated.rubric_json,
        )
        scenario_version = (
            await db.get(ScenarioVersion, scenario_version_id)
            if scenario_version_id is not None
            else None
        )
        if scenario_version is not None:
            await materialize_scenario_version_rubric_snapshots(
                db,
                scenario_version=scenario_version,
                trial=trial,
            )
        apply_status_transition(
            trial,
            target_status=TRIAL_STATUS_READY_FOR_REVIEW,
            changed_at=datetime.now(UTC),
        )
        await db.commit()
        source = generated.metadata.source
        model_name = generated.metadata.model_name
        model_version = generated.metadata.model_version
        prompt_version = generated.metadata.prompt_version
        rubric_version = generated.metadata.rubric_version
    elapsed_ms = int((perf_counter() - started) * 1000)
    logger.info(
        "scenario_generation_job_completed",
        extra={
            "trialId": trial_id,
            "jobId": generation_job_id,
            "runtimeMode": generation_config.runtime_mode,
            "provider": generation_config.provider,
            "model": generation_config.model,
            "scenarioVersionId": scenario_version_id,
            "createdScenarioVersion": created_new,
            "source": source,
            "modelName": model_name,
            "modelVersion": model_version,
            "promptVersion": prompt_version,
            "rubricVersion": rubric_version,
            "latencyMs": elapsed_ms,
        },
    )
    return {
        "status": "completed",
        "trialId": trial_id,
        "scenarioVersionId": scenario_version_id,
        "source": source,
        "modelName": model_name,
        "modelVersion": model_version,
        "promptVersion": prompt_version,
        "rubricVersion": rubric_version,
        "latencyMs": elapsed_ms,
    }


__all__ = ["handle_scenario_generation_impl"]
