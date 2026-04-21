from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import build_ai_policy_snapshot
from app.shared.database.shared_database_models_model import (
    ScenarioVersion,
    Task,
    Trial,
    User,
)
from app.trials.constants.trials_constants_trials_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.trials.constants.trials_constants_trials_blueprints_constants import (
    DEFAULT_5_DAY_BLUEPRINT,
)
from app.trials.constants.trials_constants_trials_defaults_constants import (
    DEFAULT_TEMPLATE_KEY,
)
from app.trials.services.trials_services_trials_day_five_contract_service import (
    canonical_day_five_window_override,
)


async def create_trial(
    session: AsyncSession,
    *,
    created_by: User,
    title: str = "Backend Trial",
    role: str = "Backend Engineer",
    tech_stack: str = "Node.js, PostgreSQL",
    seniority: str = "Mid",
    focus: str = "Deliver a backend feature over 5 days",
    template_key: str = DEFAULT_TEMPLATE_KEY,
    company_context: dict[str, str] | None = None,
    ai_notice_version: str | None = None,
    ai_notice_text: str | None = None,
    ai_eval_enabled_by_day: dict[str, bool] | None = None,
) -> tuple[Trial, list[Task]]:
    ai_notice_version = ai_notice_version or AI_NOTICE_DEFAULT_VERSION
    ai_notice_text = ai_notice_text or AI_NOTICE_DEFAULT_TEXT
    ai_eval_enabled_by_day = ai_eval_enabled_by_day or default_ai_eval_enabled_by_day()
    sim = Trial(
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
        day_window_overrides_enabled=True,
        day_window_overrides_json=canonical_day_five_window_override(),
    )
    session.add(sim)
    await session.flush()
    tasks: list[Task] = []
    for blueprint_task in DEFAULT_5_DAY_BLUEPRINT:
        task = Task(
            trial_id=sim.id,
            day_index=blueprint_task["day_index"],
            type=blueprint_task["type"],
            title=blueprint_task["title"],
            description=blueprint_task["description"],
            template_repo=None,
        )
        session.add(task)
        tasks.append(task)
    await session.flush()
    scenario_version = ScenarioVersion(
        trial_id=sim.id,
        version_index=1,
        status="ready",
        storyline_md=f"# {sim.title}",
        project_brief_md=(
            "# Project Brief\n\n## Business Context\n\n" f"{sim.focus or sim.title}\n"
        ),
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
        ai_policy_snapshot_json=build_ai_policy_snapshot(trial=sim),
    )
    session.add(scenario_version)
    await session.flush()
    sim.active_scenario_version_id = scenario_version.id
    sim.status = "active_inviting"
    sim.activated_at = datetime.now(UTC)
    await session.flush()
    tasks.sort(key=lambda t: t.day_index)
    return sim, tasks
