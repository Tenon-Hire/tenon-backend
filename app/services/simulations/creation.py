from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import Simulation, Task
from app.repositories.simulations.simulation import (
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
)

from .lifecycle import apply_status_transition
from .task_seed import seed_default_tasks
from .template_keys import resolve_template_key


async def create_simulation_with_tasks(
    db: AsyncSession, payload: Any, user: Any
) -> tuple[Simulation, list[Task]]:
    template_key = resolve_template_key(payload)
    started_at = datetime.now(UTC)
    sim = Simulation(
        title=payload.title,
        role=payload.role,
        tech_stack=payload.techStack,
        seniority=payload.seniority,
        focus=payload.focus,
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

    await db.commit()
    await db.refresh(sim)
    for task in created_tasks:
        await db.refresh(task)

    created_tasks.sort(key=lambda task: task.day_index)
    return sim, created_tasks
