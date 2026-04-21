"""Application module for trials services trials creation service workflows."""

from __future__ import annotations

import logging
from datetime import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Job, Task, Trial
from app.shared.jobs.repositories import repository as jobs_repo
from app.trials.constants.trials_constants_trials_ai_config_constants import (
    AI_NOTICE_DEFAULT_VERSION,
)

from .trials_services_trials_creation_builder_service import (
    build_trial_for_create,
)
from .trials_services_trials_creation_extractors_service import (
    extract_ai_fields,
    extract_company_context,
    extract_day_window_config,
)
from .trials_services_trials_day_five_contract_service import (
    enforce_day_five_trial_contract,
)
from .trials_services_trials_scenario_generation_service import (
    SCENARIO_GENERATION_JOB_MAX_ATTEMPTS,
    SCENARIO_GENERATION_JOB_TYPE,
)
from .trials_services_trials_scenario_payload_builder_service import (
    build_scenario_generation_payload,
)
from .trials_services_trials_task_seed_service import seed_default_tasks

logger = logging.getLogger(__name__)


def _scenario_generation_idempotency_key(trial_id: int) -> str:
    return f"trial:{trial_id}:scenario_generation"


def _extract_company_context(payload: Any) -> dict[str, Any] | None:
    return extract_company_context(payload)


def _extract_ai_fields(
    payload: Any,
) -> tuple[str | None, str | None, dict[str, bool] | None, dict | None]:
    return extract_ai_fields(payload)


def _extract_day_window_config(
    payload: Any,
) -> tuple[time, time, bool, dict[str, dict[str, str]] | None]:
    return extract_day_window_config(payload)


def _log_ai_config_changes(
    trial_id: int,
    actor_user_id: int,
    notice_version: str,
    eval_enabled_by_day: dict[str, bool],
) -> None:
    if notice_version != AI_NOTICE_DEFAULT_VERSION:
        logger.info(
            (
                "trial_ai_notice_version_changed trialId=%s "
                "actorUserId=%s from=%s to=%s"
            ),
            trial_id,
            actor_user_id,
            AI_NOTICE_DEFAULT_VERSION,
            notice_version,
        )
    changed_days = [
        int(day)
        for day, enabled in sorted(
            eval_enabled_by_day.items(), key=lambda item: int(item[0])
        )
        if enabled is False
    ]
    if changed_days:
        logger.info(
            (
                "trial_ai_eval_toggles_changed trialId=%s "
                "actorUserId=%s changedDays=%s"
            ),
            trial_id,
            actor_user_id,
            changed_days,
        )


async def create_trial_with_tasks(
    db: AsyncSession, payload: Any, user: Any
) -> tuple[Trial, list[Task], Job]:
    """Create trial with tasks."""
    sim, notice_version, eval_by_day = build_trial_for_create(payload, user)
    db.add(sim)
    await db.flush()
    _log_ai_config_changes(sim.id, user.id, notice_version, eval_by_day)

    created_tasks = await seed_default_tasks(db, sim.id, sim.template_key)
    enforce_day_five_trial_contract(sim, tasks=created_tasks)
    payload_json = build_scenario_generation_payload(sim)
    scenario_job = await jobs_repo.create_or_get_idempotent(
        db,
        job_type=SCENARIO_GENERATION_JOB_TYPE,
        idempotency_key=_scenario_generation_idempotency_key(sim.id),
        payload_json=payload_json,
        company_id=sim.company_id,
        correlation_id=f"trial:{sim.id}",
        max_attempts=SCENARIO_GENERATION_JOB_MAX_ATTEMPTS,
        commit=False,
    )
    await db.commit()

    created_tasks.sort(key=lambda task: task.day_index)
    return sim, created_tasks, scenario_job
