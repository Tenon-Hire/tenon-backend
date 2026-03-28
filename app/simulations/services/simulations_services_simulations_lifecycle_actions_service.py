"""Application module for simulations services simulations lifecycle actions service workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Simulation
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_ACTIVE_INVITING,
)
from app.simulations.services.simulations_services_simulations_lifecycle_access_service import (
    require_owner_for_lifecycle,
)
from app.simulations.services.simulations_services_simulations_lifecycle_transition_rules_service import (
    apply_status_transition,
)


async def _transition_owned_simulation_impl(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    target_status: str,
    now: datetime | None = None,
    require_owner: Callable[..., object] = require_owner_for_lifecycle,
    apply_transition: Callable[..., bool] = apply_status_transition,
    normalize_status: Callable[..., str | None],
    logger: logging.Logger,
) -> Simulation:
    changed_at = now or datetime.now(UTC)
    simulation = await require_owner(db, simulation_id, actor_user_id, for_update=True)
    from_status = normalize_status(simulation.status)
    pending_scenario_version_id = getattr(
        simulation, "pending_scenario_version_id", None
    )
    if (
        target_status == SIMULATION_STATUS_ACTIVE_INVITING
        and pending_scenario_version_id is not None
    ):
        raise ApiError(
            status_code=409,
            detail="Scenario approval is pending before inviting.",
            error_code="SCENARIO_APPROVAL_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": pending_scenario_version_id},
        )
    try:
        changed = apply_transition(
            simulation, target_status=target_status, changed_at=changed_at
        )
    except ApiError:
        logger.warning(
            "Rejected simulation transition simulationId=%s actorUserId=%s from=%s to=%s",
            simulation_id,
            actor_user_id,
            from_status,
            target_status,
        )
        raise
    await db.commit()
    await db.refresh(simulation)
    if changed:
        logger.info(
            "Simulation transition simulationId=%s actorUserId=%s from=%s to=%s",
            simulation.id,
            actor_user_id,
            from_status,
            normalize_status(simulation.status),
        )
    else:
        logger.info(
            "Simulation transition idempotent simulationId=%s actorUserId=%s status=%s",
            simulation.id,
            actor_user_id,
            normalize_status(simulation.status),
        )
    return simulation


__all__ = ["_transition_owned_simulation_impl"]
