from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.domains import Simulation
from app.repositories.simulations.simulation import (
    LEGACY_SIMULATION_STATUS_ACTIVE,
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_DRAFT,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_TERMINATED,
    SIMULATION_STATUSES,
)
from app.services.simulations.cleanup_jobs import enqueue_simulation_cleanup_job

logger = logging.getLogger(__name__)

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    SIMULATION_STATUS_DRAFT: {SIMULATION_STATUS_GENERATING},
    SIMULATION_STATUS_GENERATING: {SIMULATION_STATUS_READY_FOR_REVIEW},
    SIMULATION_STATUS_READY_FOR_REVIEW: {SIMULATION_STATUS_ACTIVE_INVITING},
    SIMULATION_STATUS_ACTIVE_INVITING: set(),
    SIMULATION_STATUS_TERMINATED: set(),
}


@dataclass(slots=True)
class TerminateSimulationResult:
    simulation: Simulation
    cleanup_job_ids: list[str]


def normalize_simulation_status(raw_status: str | None) -> str | None:
    if raw_status == LEGACY_SIMULATION_STATUS_ACTIVE:
        return SIMULATION_STATUS_ACTIVE_INVITING
    if raw_status in SIMULATION_STATUSES:
        return raw_status
    return None


def normalize_simulation_status_or_raise(raw_status: str | None) -> str:
    normalized = normalize_simulation_status(raw_status)
    if normalized is not None:
        return normalized
    raise ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Invalid simulation status.",
        error_code="SIMULATION_STATUS_INVALID",
        retryable=False,
        details={"status": raw_status},
    )


def _allowed_targets(current_status: str | None) -> list[str]:
    normalized = normalize_simulation_status(current_status)
    return sorted(_ALLOWED_TRANSITIONS.get(normalized or "", set()))


def _touch_timestamp(simulation: Simulation, target_status: str, at: datetime) -> None:
    if (
        target_status == SIMULATION_STATUS_GENERATING
        and simulation.generating_at is None
    ):
        simulation.generating_at = at
        return
    if (
        target_status == SIMULATION_STATUS_READY_FOR_REVIEW
        and simulation.ready_for_review_at is None
    ):
        simulation.ready_for_review_at = at
        return
    if (
        target_status == SIMULATION_STATUS_ACTIVE_INVITING
        and simulation.activated_at is None
    ):
        simulation.activated_at = at
        return
    if (
        target_status == SIMULATION_STATUS_TERMINATED
        and simulation.terminated_at is None
    ):
        simulation.terminated_at = at


def _raise_invalid_transition(current_status: str | None, target_status: str) -> None:
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Simulation status transition is not allowed.",
        error_code="SIMULATION_INVALID_STATUS_TRANSITION",
        retryable=False,
        details={
            "status": normalize_simulation_status(current_status),
            "targetStatus": target_status,
            "allowedTransitions": _allowed_targets(current_status),
        },
    )


def apply_status_transition(
    simulation: Simulation,
    *,
    target_status: str,
    changed_at: datetime | None = None,
) -> bool:
    changed_at = changed_at or datetime.now(UTC)
    current_status = normalize_simulation_status(simulation.status)
    target_status = normalize_simulation_status(target_status)

    if target_status not in SIMULATION_STATUSES:
        raise ValueError(f"Unsupported simulation status: {target_status}")

    if current_status == target_status:
        simulation.status = target_status
        _touch_timestamp(simulation, target_status, changed_at)
        return False

    if target_status == SIMULATION_STATUS_TERMINATED:
        if current_status not in SIMULATION_STATUSES:
            _raise_invalid_transition(current_status, target_status)
    elif target_status not in _ALLOWED_TRANSITIONS.get(current_status or "", set()):
        _raise_invalid_transition(current_status, target_status)

    simulation.status = target_status
    _touch_timestamp(simulation, target_status, changed_at)
    return True


def require_simulation_invitable(simulation: Simulation) -> None:
    current_status = normalize_simulation_status(simulation.status)
    if current_status == SIMULATION_STATUS_TERMINATED:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation has been terminated.",
            error_code="SIMULATION_TERMINATED",
            retryable=False,
            details={"status": current_status},
        )

    if current_status == SIMULATION_STATUS_ACTIVE_INVITING:
        return

    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Simulation is not approved for inviting.",
        error_code="SIMULATION_NOT_INVITABLE",
        retryable=False,
        details={"status": current_status},
    )


async def _load_for_lifecycle(
    db: AsyncSession, simulation_id: int, *, for_update: bool
) -> Simulation:
    stmt = select(Simulation).where(Simulation.id == simulation_id)
    if for_update:
        stmt = stmt.with_for_update()
    simulation = (await db.execute(stmt)).scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    return simulation


async def require_owner_for_lifecycle(
    db: AsyncSession,
    simulation_id: int,
    actor_user_id: int,
    *,
    for_update: bool = False,
) -> Simulation:
    simulation = await _load_for_lifecycle(db, simulation_id, for_update=for_update)
    if simulation.created_by != actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this simulation",
        )
    return simulation


async def _transition_owned_simulation(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    target_status: str,
    now: datetime | None = None,
) -> Simulation:
    changed_at = now or datetime.now(UTC)
    simulation = await require_owner_for_lifecycle(
        db, simulation_id, actor_user_id, for_update=True
    )
    from_status = normalize_simulation_status(simulation.status)

    try:
        changed = apply_status_transition(
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
            normalize_simulation_status(simulation.status),
        )
    else:
        logger.info(
            "Simulation transition idempotent simulationId=%s actorUserId=%s status=%s",
            simulation.id,
            actor_user_id,
            normalize_simulation_status(simulation.status),
        )
    return simulation


async def activate_simulation(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    now: datetime | None = None,
) -> Simulation:
    return await _transition_owned_simulation(
        db,
        simulation_id=simulation_id,
        actor_user_id=actor_user_id,
        target_status=SIMULATION_STATUS_ACTIVE_INVITING,
        now=now,
    )


async def terminate_simulation(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
) -> Simulation:
    return (
        await terminate_simulation_with_cleanup(
            db,
            simulation_id=simulation_id,
            actor_user_id=actor_user_id,
            reason=reason,
            now=now,
        )
    ).simulation


async def terminate_simulation_with_cleanup(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
) -> TerminateSimulationResult:
    changed_at = now or datetime.now(UTC)
    normalized_reason = (reason or "").strip() or None
    simulation = await require_owner_for_lifecycle(
        db, simulation_id, actor_user_id, for_update=True
    )
    from_status = normalize_simulation_status(simulation.status)

    try:
        changed = apply_status_transition(
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

    cleanup_job = await enqueue_simulation_cleanup_job(
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
        normalize_simulation_status(simulation.status),
        cleanup_job_ids,
    )
    return TerminateSimulationResult(
        simulation=simulation,
        cleanup_job_ids=cleanup_job_ids,
    )
