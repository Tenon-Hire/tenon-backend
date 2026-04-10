"""Application module for trials services trials task seed service workflows."""

from __future__ import annotations

from app.shared.database.shared_database_models_model import Task
from app.trials.constants.trials_constants_trials_blueprints_constants import (
    DEFAULT_5_DAY_BLUEPRINT,
)

from .trials_services_trials_task_templates_service import (
    _template_repo_for_task,
)


async def seed_default_tasks(db, trial_id: int, template_key: str) -> list[Task]:
    """Execute seed default tasks."""
    created_tasks: list[Task] = []
    for blueprint in DEFAULT_5_DAY_BLUEPRINT:
        task = Task(
            trial_id=trial_id,
            day_index=blueprint["day_index"],
            type=blueprint["type"],
            title=blueprint["title"],
            description=blueprint["description"],
            template_repo=_template_repo_for_task(
                blueprint["day_index"], blueprint["type"], template_key
            ),
        )
        db.add(task)
        created_tasks.append(task)
    return created_tasks
