"""Application module for simulations services simulations lifecycle termination service workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Simulation
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_TERMINATED,
)
from app.simulations.services.simulations_services_simulations_cleanup_jobs_service import (
    enqueue_simulation_cleanup_job,
)
from app.simulations.services.simulations_services_simulations_lifecycle_access_service import (
    require_owner_for_lifecycle,
)
from app.simulations.services.simulations_services_simulations_lifecycle_transition_rules_service import (
    apply_status_transition,
)


@dataclass(slots=True)
class TerminateSimulationResult:
    """Represent terminate simulation result data and behavior."""

    simulation: Simulation
    cleanup_job_ids: list[str]


async def terminate_simulation_with_cleanup_impl(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
    require_owner: Callable[..., object] = require_owner_for_lifecycle,
    apply_transition: Callable[..., bool] = apply_status_transition,
    enqueue_cleanup_job: Callable[..., object] = enqueue_simulation_cleanup_job,
    normalize_status: Callable[..., str | None],
    logger: logging.Logger,
) -> TerminateSimulationResult:
    """Terminate simulation with cleanup impl."""
    changed_at = now or datetime.now(UTC)
    normalized_reason = (reason or "").strip() or None
    simulation = await require_owner(db, simulation_id, actor_user_id, for_update=True)
    from_status = normalize_status(simulation.status)
    try:
        changed = apply_transition(
            simulation,
            target_status=SIMULATION_STATUS_TERMINATED,
            changed_at=changed_at,
        )
    except ApiError:
        logger.warning(
            "Rejected simulation termination simulationId=%s actorUserId=%s from=%s",
            simulation_id,
            actor_user_id,
            from_status,
        )
        raise
    if changed:
        simulation.terminated_by_recruiter_id = actor_user_id
        if normalized_reason is not None:
            simulation.terminated_reason = normalized_reason
    cleanup_job = await enqueue_cleanup_job(
        db,
        simulation=simulation,
        terminated_by_user_id=actor_user_id,
        reason=normalized_reason,
        commit=False,
    )
    await db.commit()
    await db.refresh(simulation)
    cleanup_job_ids = [str(cleanup_job.id)]
    logger.info(
        "Simulation terminated simulationId=%s actorUserId=%s from=%s to=%s cleanupJobIds=%s",
        simulation.id,
        actor_user_id,
        from_status,
        normalize_status(simulation.status),
        cleanup_job_ids,
    )
    return TerminateSimulationResult(
        simulation=simulation, cleanup_job_ids=cleanup_job_ids
    )


__all__ = ["TerminateSimulationResult", "terminate_simulation_with_cleanup_impl"]
