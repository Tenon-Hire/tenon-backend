from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.shared.database.shared_database_models_model import (
    Company,
    Job,
    ScenarioVersion,
    Trial,
    User,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials import services as sim_service
from app.trials.services import (
    trials_services_trials_lifecycle_service as lifecycle_service,
)


def _trial(status: str) -> Trial:
    return Trial(
        company_id=1,
        title="Lifecycle",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Test",
        scenario_template="default-5day-node-postgres",
        created_by=1,
        status=status,
    )


async def _attach_active_scenario(async_session, trial: Trial) -> None:
    scenario = ScenarioVersion(
        trial_id=trial.id,
        version_index=1,
        status="ready",
        storyline_md=f"# {trial.title}",
        task_prompts_json=[],
        rubric_json={},
        focus_notes=trial.focus or "",
        template_key=trial.template_key,
        tech_stack=trial.tech_stack,
        seniority=trial.seniority,
    )
    async_session.add(scenario)
    await async_session.flush()
    trial.active_scenario_version_id = scenario.id
    await async_session.flush()


__all__ = [name for name in globals() if not name.startswith("__")]
