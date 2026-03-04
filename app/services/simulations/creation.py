from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import Simulation, Task
from app.domains.simulations.schemas import (
    normalize_eval_enabled_by_day,
    normalize_role_level,
)
from app.repositories.jobs import repository as jobs_repo
from app.repositories.simulations.simulation import (
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
)

from .lifecycle import apply_status_transition
from .scenario_payload_builder import build_scenario_generation_payload
from .task_seed import seed_default_tasks
from .template_keys import resolve_template_key

SCENARIO_GENERATION_JOB_TYPE = "scenario_generation"


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


async def create_simulation_with_tasks(
    db: AsyncSession, payload: Any, user: Any
) -> tuple[Simulation, list[Task]]:
    template_key = resolve_template_key(payload)
    started_at = datetime.now(UTC)
    company_context = _extract_company_context(payload)
    ai_notice_version, ai_notice_text, ai_eval_enabled_by_day = _extract_ai_fields(
        payload
    )
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
        ai_notice_version=ai_notice_version,
        ai_notice_text=ai_notice_text,
        ai_eval_enabled_by_day=ai_eval_enabled_by_day,
        scenario_template="default-5day-node-postgres",
        company_id=user.company_id,
        created_by=user.id,
        template_key=template_key,
        status=SIMULATION_STATUS_GENERATING,
        generating_at=started_at,
    )
    db.add(sim)
    await db.flush()

    created_tasks = await seed_default_tasks(db, sim.id, template_key)
    # Creation is currently synchronous, so "generating" can be short-lived.
    apply_status_transition(
        sim,
        target_status=SIMULATION_STATUS_READY_FOR_REVIEW,
        changed_at=datetime.now(UTC),
    )

    await db.flush()

    payload_json = build_scenario_generation_payload(sim)
    await jobs_repo.create_or_get_idempotent(
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

    created_tasks.sort(key=lambda task: task.day_index)
    return sim, created_tasks
