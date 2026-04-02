from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import build_ai_policy_snapshot
from app.shared.database.shared_database_models_model import (
    ScenarioVersion,
    Simulation,
    Task,
    User,
)
from app.simulations.constants.simulations_constants_simulations_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.simulations.constants.simulations_constants_simulations_blueprints_constants import (
    DEFAULT_5_DAY_BLUEPRINT,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    DEFAULT_TEMPLATE_KEY,
    resolve_template_repo_full_name,
)


async def create_simulation(
    session: AsyncSession,
    *,
    created_by: User,
    title: str = "Backend Simulation",
    role: str = "Backend Engineer",
    tech_stack: str = "Node.js, PostgreSQL",
    seniority: str = "Mid",
    focus: str = "Deliver a backend feature over 5 days",
    template_key: str = DEFAULT_TEMPLATE_KEY,
    company_context: dict[str, str] | None = None,
    ai_notice_version: str | None = None,
    ai_notice_text: str | None = None,
    ai_eval_enabled_by_day: dict[str, bool] | None = None,
) -> tuple[Simulation, list[Task]]:
    ai_notice_version = ai_notice_version or AI_NOTICE_DEFAULT_VERSION
    ai_notice_text = ai_notice_text or AI_NOTICE_DEFAULT_TEXT
    ai_eval_enabled_by_day = ai_eval_enabled_by_day or default_ai_eval_enabled_by_day()
    sim = Simulation(
        company_id=created_by.company_id,
        title=title,
        role=role,
        tech_stack=tech_stack,
        seniority=seniority,
        focus=focus,
        scenario_template="default-5day-node-postgres",
        created_by=created_by.id,
        status="generating",
        generating_at=datetime.now(UTC),
        template_key=template_key,
        company_context=company_context,
        ai_notice_version=ai_notice_version,
        ai_notice_text=ai_notice_text,
        ai_eval_enabled_by_day=ai_eval_enabled_by_day,
    )
    session.add(sim)
    await session.flush()
    tasks: list[Task] = []
    for blueprint_task in DEFAULT_5_DAY_BLUEPRINT:
        task = Task(
            simulation_id=sim.id,
            day_index=blueprint_task["day_index"],
            type=blueprint_task["type"],
            title=blueprint_task["title"],
            description=blueprint_task["description"],
            template_repo=(
                resolve_template_repo_full_name(template_key)
                if blueprint_task["type"] in {"code", "debug"}
                else None
            ),
        )
        session.add(task)
        tasks.append(task)
    await session.flush()
    scenario_version = ScenarioVersion(
        simulation_id=sim.id,
        version_index=1,
        status="ready",
        storyline_md=f"# {sim.title}",
        task_prompts_json=[
            {
                "dayIndex": t.day_index,
                "type": t.type,
                "title": t.title,
                "description": t.description,
            }
            for t in sorted(tasks, key=lambda item: item.day_index)
        ],
        rubric_json={},
        focus_notes=sim.focus or "",
        template_key=sim.template_key,
        tech_stack=sim.tech_stack,
        seniority=sim.seniority,
        ai_policy_snapshot_json=build_ai_policy_snapshot(simulation=sim),
    )
    session.add(scenario_version)
    await session.flush()
    sim.active_scenario_version_id = scenario_version.id
    sim.status = "active_inviting"
    sim.activated_at = datetime.now(UTC)
    await session.flush()
    tasks.sort(key=lambda t: t.day_index)
    return sim, tasks
