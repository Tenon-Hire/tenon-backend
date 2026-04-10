"""Application module for trials services trials update service workflows."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import merge_prompt_override_payloads
from app.shared.database.shared_database_models_model import Task, Trial
from app.trials.schemas.trials_schemas_trials_core_schema import (
    resolve_trial_ai_fields,
)

from .trials_services_trials_ownership_service import (
    require_owned_trial_with_tasks,
)

logger = logging.getLogger(__name__)


def _ai_payload_field_set(ai_payload: Any) -> set[str]:
    fields = getattr(ai_payload, "model_fields_set", set())
    if isinstance(fields, set):
        return fields
    return set()


async def update_trial(
    db: AsyncSession,
    *,
    trial_id: int,
    actor_user_id: int,
    payload: Any,
) -> tuple[Trial, list[Task]]:
    """Update trial."""
    trial, tasks = await require_owned_trial_with_tasks(
        db,
        trial_id,
        actor_user_id,
    )

    ai_payload = getattr(payload, "ai", None)
    if ai_payload is None:
        return trial, tasks

    (
        previous_notice_version,
        _previous_notice_text,
        previous_eval,
    ) = resolve_trial_ai_fields(
        notice_version=getattr(trial, "ai_notice_version", None),
        notice_text=getattr(trial, "ai_notice_text", None),
        eval_enabled_by_day=getattr(trial, "ai_eval_enabled_by_day", None),
    )
    ai_fields_set = _ai_payload_field_set(ai_payload)

    incoming_notice_version = (
        ai_payload.notice_version if "notice_version" in ai_fields_set else None
    )
    incoming_notice_text = (
        ai_payload.notice_text if "notice_text" in ai_fields_set else None
    )
    incoming_eval_enabled_by_day = (
        ai_payload.eval_enabled_by_day
        if "eval_enabled_by_day" in ai_fields_set
        else None
    )
    incoming_prompt_overrides = (
        ai_payload.prompt_overrides if "prompt_overrides" in ai_fields_set else None
    )

    (
        resolved_notice_version,
        resolved_notice_text,
        resolved_eval,
    ) = resolve_trial_ai_fields(
        notice_version=incoming_notice_version,
        notice_text=incoming_notice_text,
        eval_enabled_by_day=incoming_eval_enabled_by_day,
        fallback_notice_version=getattr(trial, "ai_notice_version", None),
        fallback_notice_text=getattr(trial, "ai_notice_text", None),
        fallback_eval_enabled_by_day=getattr(
            trial,
            "ai_eval_enabled_by_day",
            None,
        ),
    )

    trial.ai_notice_version = resolved_notice_version
    trial.ai_notice_text = resolved_notice_text
    trial.ai_eval_enabled_by_day = resolved_eval
    trial.ai_prompt_overrides_json = merge_prompt_override_payloads(
        incoming=incoming_prompt_overrides,
        fallback=getattr(trial, "ai_prompt_overrides_json", None),
    )

    if previous_notice_version != resolved_notice_version:
        logger.info(
            (
                "trial_ai_notice_version_changed trialId=%s "
                "actorUserId=%s from=%s to=%s"
            ),
            trial.id,
            actor_user_id,
            previous_notice_version,
            resolved_notice_version,
        )

    changed_days = [
        int(day)
        for day in sorted(resolved_eval.keys(), key=int)
        if previous_eval.get(day) != resolved_eval.get(day)
    ]
    if changed_days:
        logger.info(
            (
                "trial_ai_eval_toggles_changed trialId=%s "
                "actorUserId=%s changedDays=%s"
            ),
            trial.id,
            actor_user_id,
            changed_days,
        )

    await db.commit()
    await db.refresh(trial)
    for task in tasks:
        await db.refresh(task)
    return trial, tasks


__all__ = ["update_trial"]
