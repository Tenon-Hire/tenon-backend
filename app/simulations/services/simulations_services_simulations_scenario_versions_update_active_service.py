"""Application module for simulations services simulations scenario versions update active service workflows."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_DRAFT,
    SCENARIO_VERSION_STATUS_READY,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_access_service import (
    get_active_scenario_for_update,
    require_owned_simulation_for_update,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_defaults_service import (
    ensure_scenario_version_mutable,
)

logger = logging.getLogger(__name__)


async def update_active_scenario_version(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    updates: dict[str, Any],
):
    """Update active scenario version."""
    simulation = await require_owned_simulation_for_update(
        db, simulation_id, actor_user_id
    )
    active = await get_active_scenario_for_update(db, simulation)
    ensure_scenario_version_mutable(active)
    _apply_simple_updates(active, updates)
    if "status" in updates:
        active.status = _validate_status_update(updates["status"])
    await db.commit()
    await db.refresh(active)
    logger.info(
        "Scenario version updated simulationId=%s scenarioVersionId=%s status=%s",
        simulation.id,
        active.id,
        active.status,
    )
    return active


def _apply_simple_updates(active, updates: dict[str, Any]) -> None:
    if "storyline_md" in updates:
        active.storyline_md = str(updates["storyline_md"] or "")
    if "task_prompts_json" in updates:
        active.task_prompts_json = (
            [] if updates["task_prompts_json"] is None else updates["task_prompts_json"]
        )
    if "rubric_json" in updates:
        active.rubric_json = (
            {} if updates["rubric_json"] is None else updates["rubric_json"]
        )
    if "focus_notes" in updates:
        active.focus_notes = str(updates["focus_notes"] or "")


def _validate_status_update(value: Any) -> str:
    next_status = str(value)
    if next_status in {SCENARIO_VERSION_STATUS_DRAFT, SCENARIO_VERSION_STATUS_READY}:
        return next_status
    raise ApiError(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Invalid scenario status.",
        error_code="SCENARIO_STATUS_INVALID",
        retryable=False,
        details={
            "allowed": [SCENARIO_VERSION_STATUS_DRAFT, SCENARIO_VERSION_STATUS_READY]
        },
    )
