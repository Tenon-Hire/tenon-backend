from __future__ import annotations

import logging
from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import Job, Simulation, Task
from app.domains.simulations.ai_config import AI_NOTICE_DEFAULT_VERSION
from app.domains.simulations.schemas import (
    normalize_eval_enabled_by_day,
    normalize_role_level,
    resolve_simulation_ai_fields,
)
from app.repositories.jobs import repository as jobs_repo
from app.repositories.simulations.simulation import (
    SIMULATION_STATUS_GENERATING,
)

from .scenario_generation import SCENARIO_GENERATION_JOB_TYPE
from .scenario_payload_builder import build_scenario_generation_payload
from .task_seed import seed_default_tasks
from .template_keys import resolve_template_key

logger = logging.getLogger(__name__)


def _scenario_generation_idempotency_key(simulation_id: int) -> str:
    return f"simulation:{simulation_id}:scenario_generation"


def _extract_company_context(payload: Any) -> dict[str, Any] | None:
    raw_company_context = getattr(
        payload, "company_context", getattr(payload, "companyContext", None)
    )
    if raw_company_context is None:
        return None
    if hasattr(raw_company_context, "model_dump"):
        return raw_company_context.model_dump(by_alias=True, exclude_none=True)
    if isinstance(raw_company_context, dict):
        return dict(raw_company_context)
    return None


def _extract_ai_fields(
    payload: Any,
) -> tuple[str | None, str | None, dict[str, bool] | None]:
    raw_ai = getattr(payload, "ai", None)
    if raw_ai is None:
        return None, None, None

    if isinstance(raw_ai, dict):
        notice_version = raw_ai.get("noticeVersion")
        notice_text = raw_ai.get("noticeText")
        eval_by_day = raw_ai.get("evalEnabledByDay")
    else:
        notice_version = getattr(raw_ai, "notice_version", None)
        if notice_version is None:
            notice_version = getattr(raw_ai, "noticeVersion", None)
        notice_text = getattr(raw_ai, "notice_text", None)
        if notice_text is None:
            notice_text = getattr(raw_ai, "noticeText", None)
        eval_by_day = getattr(raw_ai, "eval_enabled_by_day", None)
        if eval_by_day is None:
            eval_by_day = getattr(raw_ai, "evalEnabledByDay", None)

    normalized_eval = normalize_eval_enabled_by_day(eval_by_day, strict=False)
    return notice_version, notice_text, normalized_eval


def _extract_day_window_config(
    payload: Any,
) -> tuple[time, time, bool, dict[str, dict[str, str]] | None]:
    day_window_start_local = getattr(payload, "dayWindowStartLocal", None) or time(
        hour=9, minute=0
    )
    day_window_end_local = getattr(payload, "dayWindowEndLocal", None) or time(
        hour=17, minute=0
    )
    overrides_enabled = bool(getattr(payload, "dayWindowOverridesEnabled", False))
    raw_overrides = getattr(payload, "dayWindowOverrides", None)

    if raw_overrides is None:
        return day_window_start_local, day_window_end_local, overrides_enabled, None

    normalized_overrides: dict[str, dict[str, str]] = {}
    for raw_day, raw_window in raw_overrides.items():
        if hasattr(raw_window, "model_dump"):
            serialized = raw_window.model_dump(by_alias=True)
        elif isinstance(raw_window, dict):
            serialized = dict(raw_window)
        else:
            continue
        normalized_overrides[str(raw_day)] = {
            "startLocal": str(serialized.get("startLocal")),
            "endLocal": str(serialized.get("endLocal")),
        }
    return (
        day_window_start_local,
        day_window_end_local,
        overrides_enabled,
        normalized_overrides or None,
    )


async def create_simulation_with_tasks(
    db: AsyncSession, payload: Any, user: Any
) -> tuple[Simulation, list[Task], Job]:
    template_key = resolve_template_key(payload)
    started_at = datetime.now(UTC)
    company_context = _extract_company_context(payload)
    ai_notice_version, ai_notice_text, ai_eval_enabled_by_day = _extract_ai_fields(
        payload
    )
    (
        resolved_notice_version,
        resolved_notice_text,
        resolved_eval_by_day,
    ) = resolve_simulation_ai_fields(
        notice_version=ai_notice_version,
        notice_text=ai_notice_text,
        eval_enabled_by_day=ai_eval_enabled_by_day,
    )
    (
        day_window_start_local,
        day_window_end_local,
        day_window_overrides_enabled,
        day_window_overrides_json,
    ) = _extract_day_window_config(payload)
    raw_seniority = getattr(payload, "seniority", None)
    normalized_seniority = normalize_role_level(raw_seniority)
    seniority_value = normalized_seniority or raw_seniority
    sim = Simulation(
        title=payload.title,
        role=payload.role,
        tech_stack=getattr(payload, "techStack", getattr(payload, "tech_stack", "")),
        seniority=seniority_value,
        focus=payload.focus,
        company_context=company_context,
        ai_notice_version=resolved_notice_version,
        ai_notice_text=resolved_notice_text,
        ai_eval_enabled_by_day=resolved_eval_by_day,
        day_window_start_local=day_window_start_local,
        day_window_end_local=day_window_end_local,
        day_window_overrides_enabled=day_window_overrides_enabled,
        day_window_overrides_json=day_window_overrides_json,
        scenario_template="default-5day-node-postgres",
        company_id=user.company_id,
        created_by=user.id,
        template_key=template_key,
        status=SIMULATION_STATUS_GENERATING,
        generating_at=started_at,
    )
    db.add(sim)
    await db.flush()

    if resolved_notice_version != AI_NOTICE_DEFAULT_VERSION:
        logger.info(
            (
                "simulation_ai_notice_version_changed simulationId=%s "
                "actorUserId=%s from=%s to=%s"
            ),
            sim.id,
            user.id,
            AI_NOTICE_DEFAULT_VERSION,
            resolved_notice_version,
        )
    changed_days = [
        int(day)
        for day, enabled in sorted(
            resolved_eval_by_day.items(), key=lambda item: int(item[0])
        )
        if enabled is False
    ]
    if changed_days:
        logger.info(
            (
                "simulation_ai_eval_toggles_changed simulationId=%s "
                "actorUserId=%s changedDays=%s"
            ),
            sim.id,
            user.id,
            changed_days,
        )

    created_tasks = await seed_default_tasks(db, sim.id, template_key)

    payload_json = build_scenario_generation_payload(sim)
    # First idempotency layer: exactly one scenario_generation enqueue key per
    # simulation create flow.
    scenario_job = await jobs_repo.create_or_get_idempotent(
        db,
        job_type=SCENARIO_GENERATION_JOB_TYPE,
        idempotency_key=_scenario_generation_idempotency_key(sim.id),
        payload_json=payload_json,
        company_id=sim.company_id,
        correlation_id=f"simulation:{sim.id}",
        commit=False,
    )
    await db.commit()

    await db.refresh(sim)
    for task in created_tasks:
        await db.refresh(task)
    await db.refresh(scenario_job)

    created_tasks.sort(key=lambda task: task.day_index)
    return sim, created_tasks, scenario_job
