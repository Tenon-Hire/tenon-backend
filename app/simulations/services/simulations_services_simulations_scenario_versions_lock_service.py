"""Application module for simulations services simulations scenario versions lock service workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import ScenarioVersion, Simulation
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_LOCKED,
    SCENARIO_VERSION_STATUS_READY,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_access_service import (
    get_active_scenario_for_update,
)

logger = logging.getLogger(__name__)


async def lock_active_scenario_for_invites(
    db: AsyncSession,
    *,
    simulation_id: int,
    now: datetime | None = None,
    simulation: Simulation | None = None,
) -> ScenarioVersion:
    """Execute lock active scenario for invites."""
    lock_at = now or datetime.now(UTC)
    locked_simulation = simulation
    if locked_simulation is None:
        locked_simulation = (
            await db.execute(
                select(Simulation)
                .where(Simulation.id == simulation_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if locked_simulation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
            )
    active = await get_active_scenario_for_update(db, locked_simulation)
    if active.status == SCENARIO_VERSION_STATUS_LOCKED:
        return active
    if active.status != SCENARIO_VERSION_STATUS_READY:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is not approved for inviting.",
            error_code="SCENARIO_NOT_READY",
            retryable=False,
            details={"status": active.status},
        )
    active.status = SCENARIO_VERSION_STATUS_LOCKED
    active.locked_at = lock_at
    logger.info(
        "Scenario version locked simulationId=%s scenarioVersionId=%s lockedAt=%s",
        locked_simulation.id,
        active.id,
        active.locked_at.isoformat() if active.locked_at else None,
    )
    return active
