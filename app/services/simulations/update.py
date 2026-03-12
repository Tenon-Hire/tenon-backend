from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import Simulation, Task
from app.domains.simulations.schemas import resolve_simulation_ai_fields

from .ownership import require_owned_simulation_with_tasks

logger = logging.getLogger(__name__)


def _ai_payload_field_set(ai_payload: Any) -> set[str]:
    fields = getattr(ai_payload, "model_fields_set", set())
    if isinstance(fields, set):
        return fields
    return set()


async def update_simulation(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    payload: Any,
) -> tuple[Simulation, list[Task]]:
    simulation, tasks = await require_owned_simulation_with_tasks(
        db,
        simulation_id,
        actor_user_id,
    )

    ai_payload = getattr(payload, "ai", None)
    if ai_payload is None:
        return simulation, tasks

    (
        previous_notice_version,
        _previous_notice_text,
        previous_eval,
    ) = resolve_simulation_ai_fields(
        notice_version=getattr(simulation, "ai_notice_version", None),
        notice_text=getattr(simulation, "ai_notice_text", None),
        eval_enabled_by_day=getattr(simulation, "ai_eval_enabled_by_day", None),
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

    (
        resolved_notice_version,
        resolved_notice_text,
        resolved_eval,
    ) = resolve_simulation_ai_fields(
        notice_version=incoming_notice_version,
        notice_text=incoming_notice_text,
        eval_enabled_by_day=incoming_eval_enabled_by_day,
        fallback_notice_version=getattr(simulation, "ai_notice_version", None),
        fallback_notice_text=getattr(simulation, "ai_notice_text", None),
        fallback_eval_enabled_by_day=getattr(
            simulation,
            "ai_eval_enabled_by_day",
            None,
        ),
    )

    simulation.ai_notice_version = resolved_notice_version
    simulation.ai_notice_text = resolved_notice_text
    simulation.ai_eval_enabled_by_day = resolved_eval

    if previous_notice_version != resolved_notice_version:
        logger.info(
            (
                "simulation_ai_notice_version_changed simulationId=%s "
                "actorUserId=%s from=%s to=%s"
            ),
            simulation.id,
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
                "simulation_ai_eval_toggles_changed simulationId=%s "
                "actorUserId=%s changedDays=%s"
            ),
            simulation.id,
            actor_user_id,
            changed_days,
        )

    await db.commit()
    await db.refresh(simulation)
    for task in tasks:
        await db.refresh(task)
    return simulation, tasks


__all__ = ["update_simulation"]
