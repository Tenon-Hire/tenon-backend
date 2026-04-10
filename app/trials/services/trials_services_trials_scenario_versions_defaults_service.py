"""Application module for trials services trials scenario versions defaults service workflows."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import status

from app.shared.database.shared_database_models_model import (
    ScenarioVersion,
    Task,
    Trial,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_LOCKED,
)

logger = logging.getLogger(__name__)


def default_storyline_md(trial: Trial) -> str:
    """Execute default storyline md."""
    title = (trial.title or "").strip()
    role = (trial.role or "").strip()
    scenario_template = (trial.scenario_template or "").strip()
    return (
        f"# {title}\n\n" f"Role: {role}\n" f"Template: {scenario_template}\n"
    ).strip()


def task_prompts_payload(tasks: list[Task]) -> list[dict[str, Any]]:
    """Execute task prompts payload."""
    return [
        {
            "dayIndex": task.day_index,
            "type": task.type,
            "title": task.title,
            "description": task.description,
        }
        for task in sorted(tasks, key=lambda item: item.day_index)
    ]


def ensure_scenario_version_mutable(scenario_version: ScenarioVersion) -> None:
    """Ensure scenario version mutable."""
    if (
        scenario_version.status != SCENARIO_VERSION_STATUS_LOCKED
        and scenario_version.locked_at is None
    ):
        return
    logger.warning(
        "Scenario mutation blocked because version is locked scenarioVersionId=%s trialId=%s",
        scenario_version.id,
        scenario_version.trial_id,
    )
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Scenario version is locked.",
        error_code="SCENARIO_LOCKED",
        retryable=False,
        details={},
        compact_response=True,
    )
