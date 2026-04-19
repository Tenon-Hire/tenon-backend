"""Application module for trials services trials scenario versions regeneration service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    Job,
    ScenarioVersion,
    Trial,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.scenario_versions import (
    trials_repositories_scenario_versions_trials_scenario_versions_repository as scenario_repo,
)
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_GENERATING,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_GENERATING,
    TRIAL_STATUS_READY_FOR_REVIEW,
)
from app.trials.services.trials_services_trials_lifecycle_service import (
    apply_status_transition,
)
from app.trials.services.trials_services_trials_scenario_generation_service import (
    SCENARIO_GENERATION_JOB_MAX_ATTEMPTS,
    SCENARIO_GENERATION_JOB_TYPE,
)
from app.trials.services.trials_services_trials_scenario_payload_builder_service import (
    build_scenario_generation_payload,
)
from app.trials.services.trials_services_trials_scenario_versions_access_service import (
    get_active_scenario_for_update,
    require_owned_trial_for_update,
    scenario_generation_idempotency_key,
)
from app.trials.services.trials_services_trials_scenario_versions_regeneration_helpers_service import (
    clone_pending_scenario,
    enqueue_regeneration_job,
)

logger = logging.getLogger(__name__)
PUBLIC_JOB_STATUS_FAILED = "failed"


async def _load_latest_scenario_generation_job(
    db: AsyncSession, *, trial_id: int, company_id: int
) -> Job | None:
    stmt = (
        select(Job)
        .where(
            Job.company_id == company_id,
            Job.job_type == SCENARIO_GENERATION_JOB_TYPE,
            Job.correlation_id.like(f"trial:{trial_id}%"),
        )
        .order_by(desc(Job.created_at), desc(Job.updated_at))
    )
    return await db.scalar(stmt)


async def _restore_placeholder_scenario_version(
    db: AsyncSession,
    *,
    trial: Trial,
) -> ScenarioVersion:
    existing = (
        await db.execute(
            select(ScenarioVersion)
            .where(ScenarioVersion.trial_id == trial.id)
            .order_by(ScenarioVersion.version_index.asc(), ScenarioVersion.id.asc())
            .with_for_update()
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = ScenarioVersion(
            trial_id=trial.id,
            version_index=1,
            status=SCENARIO_VERSION_STATUS_GENERATING,
            storyline_md="",
            task_prompts_json=[],
            project_brief_md="",
            rubric_json={},
            focus_notes=trial.focus or "",
            template_key=trial.template_key,
            tech_stack=trial.tech_stack,
            seniority=trial.seniority,
        )
        db.add(existing)
        await db.flush()
    else:
        existing.status = SCENARIO_VERSION_STATUS_GENERATING
        existing.storyline_md = ""
        existing.task_prompts_json = []
        existing.project_brief_md = ""
        existing.rubric_json = {}
        existing.focus_notes = trial.focus or ""
        existing.template_key = trial.template_key
        existing.tech_stack = trial.tech_stack
        existing.seniority = trial.seniority
        existing.locked_at = None
        await db.flush()
    trial.active_scenario_version_id = existing.id
    return existing


async def regenerate_active_scenario_version(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
) -> tuple[Trial, ScenarioVersion]:
    """Regenerate active scenario version."""
    trial, regenerated, _job = await request_scenario_regeneration(
        db, trial_id=trial_id, actor_user_id=actor_user_id
    )
    return trial, regenerated


async def request_scenario_regeneration(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
) -> tuple[Trial, ScenarioVersion, Job]:
    """Execute request scenario regeneration."""
    regenerated_at = datetime.now(UTC)
    trial = await require_owned_trial_for_update(db, trial_id, actor_user_id)
    latest_scenario_job = await _load_latest_scenario_generation_job(
        db, trial_id=trial.id, company_id=trial.company_id
    )
    if trial.pending_scenario_version_id is not None:
        raise ApiError(
            status_code=409,
            detail="Scenario regeneration is already pending approval.",
            error_code="SCENARIO_REGENERATION_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": trial.pending_scenario_version_id},
        )
    try:
        active = await get_active_scenario_for_update(db, trial)
    except ApiError as exc:
        if exc.error_code != "SCENARIO_ACTIVE_VERSION_MISSING":
            raise
        latest_job_is_failed = bool(
            latest_scenario_job
            and getattr(latest_scenario_job, "status", None)
            in {JOB_STATUS_DEAD_LETTER, PUBLIC_JOB_STATUS_FAILED}
        )
        if trial.status != TRIAL_STATUS_GENERATING and not latest_job_is_failed:
            raise
        active = None

    if active is None:
        regenerated = await _restore_placeholder_scenario_version(db, trial=trial)
        scenario_job = latest_scenario_job
        if scenario_job is None:
            payload_json = build_scenario_generation_payload(trial)
            scenario_job = await jobs_repo.create_or_get_idempotent(
                db,
                job_type=SCENARIO_GENERATION_JOB_TYPE,
                idempotency_key=scenario_generation_idempotency_key(trial.id),
                payload_json=payload_json,
                company_id=trial.company_id,
                correlation_id=f"trial:{trial.id}",
                max_attempts=SCENARIO_GENERATION_JOB_MAX_ATTEMPTS,
                commit=False,
            )
        elif scenario_job.status == JOB_STATUS_DEAD_LETTER:
            await jobs_repo.requeue_dead_letter_jobs(
                db, now=regenerated_at, job_ids=[str(scenario_job.id)]
            )
        await db.commit()
        await db.refresh(trial)
        await db.refresh(regenerated)
        await db.refresh(scenario_job)
        logger.info(
            "Scenario generation retry restored placeholder trialId=%s scenarioVersionId=%s jobId=%s",
            trial.id,
            regenerated.id,
            scenario_job.id,
        )
        return trial, regenerated, scenario_job

    new_index = await scenario_repo.next_version_index(db, trial.id)
    regenerated = clone_pending_scenario(trial, active, new_index)
    db.add(regenerated)
    await db.flush()
    trial.pending_scenario_version_id = regenerated.id
    apply_status_transition(
        trial,
        target_status=TRIAL_STATUS_READY_FOR_REVIEW,
        changed_at=regenerated_at,
    )
    scenario_job = await enqueue_regeneration_job(db, trial, regenerated)
    await db.commit()
    await db.refresh(trial)
    await db.refresh(regenerated)
    await db.refresh(scenario_job)
    logger.info(
        "Scenario regeneration requested trialId=%s fromScenarioVersionId=%s toScenarioVersionId=%s versionIndex=%s jobId=%s",
        trial.id,
        active.id,
        regenerated.id,
        regenerated.version_index,
        scenario_job.id,
    )
    return trial, regenerated, scenario_job
