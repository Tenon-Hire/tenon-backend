"""Application module for simulations services simulations scenario versions patch utils service workflows."""

from __future__ import annotations

import copy
import logging
from typing import Any

from fastapi import status

from app.shared.database.shared_database_models_model import ScenarioVersion, Simulation
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_LOCKED,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_constants import (
    SCENARIO_NOT_EDITABLE_ERROR_CODE,
    SCENARIO_PATCH_DEEP_COPY_FIELDS,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_patching_service import (
    is_editable_scenario_status,
    is_editable_simulation_status,
)

logger = logging.getLogger(__name__)


def ensure_patch_allowed(
    simulation: Simulation, scenario_version: ScenarioVersion, actor_user_id: int
) -> None:
    """Ensure patch allowed."""
    if (
        scenario_version.status == SCENARIO_VERSION_STATUS_LOCKED
        or scenario_version.locked_at is not None
    ):
        logger.warning(
            "Scenario patch blocked because version is locked simulationId=%s scenarioVersionId=%s recruiterId=%s",
            simulation.id,
            scenario_version.id,
            actor_user_id,
        )
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is locked.",
            error_code="SCENARIO_LOCKED",
            retryable=False,
            details={},
            compact_response=True,
        )
    if not is_editable_simulation_status(simulation.status):
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is not editable in the current simulation status.",
            error_code=SCENARIO_NOT_EDITABLE_ERROR_CODE,
            retryable=False,
            details={"simulationStatus": simulation.status},
        )
    if is_editable_scenario_status(scenario_version.status):
        return
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Scenario version is not editable in the current status.",
        error_code=SCENARIO_NOT_EDITABLE_ERROR_CODE,
        retryable=False,
        details={"scenarioStatus": scenario_version.status},
    )


def snapshot_editable_state(scenario_version: ScenarioVersion) -> dict[str, Any]:
    """Execute snapshot editable state."""
    return {
        "storyline_md": copy.deepcopy(scenario_version.storyline_md),
        "task_prompts_json": copy.deepcopy(scenario_version.task_prompts_json),
        "rubric_json": copy.deepcopy(scenario_version.rubric_json),
        "focus_notes": copy.deepcopy(scenario_version.focus_notes),
    }


def merge_patch_state(
    before_state: dict[str, Any], updates: dict[str, Any], candidate_fields: list[str]
) -> dict[str, Any]:
    """Execute merge patch state."""
    merged_state = copy.deepcopy(before_state)
    for field_name in candidate_fields:
        value = updates[field_name]
        merged_state[field_name] = (
            copy.deepcopy(value)
            if field_name in SCENARIO_PATCH_DEEP_COPY_FIELDS
            else value
        )
    return merged_state


def apply_normalized_patch(
    scenario_version: ScenarioVersion, normalized_state: dict[str, Any]
) -> None:
    """Apply normalized patch."""
    scenario_version.storyline_md = normalized_state["storyline_md"]
    scenario_version.task_prompts_json = normalized_state["task_prompts_json"]
    scenario_version.rubric_json = normalized_state["rubric_json"]
    scenario_version.focus_notes = normalized_state["focus_notes"]
