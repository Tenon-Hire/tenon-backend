from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import Job, Simulation
from app.repositories.jobs import repository as jobs_repo

SIMULATION_CLEANUP_JOB_TYPE = "simulation_cleanup"
SIMULATION_CLEANUP_MAX_ATTEMPTS = 8


def simulation_cleanup_idempotency_key(simulation_id: int) -> str:
    return f"simulation_cleanup:{simulation_id}"


def build_simulation_cleanup_payload(
    simulation: Simulation,
    *,
    terminated_by_user_id: int,
    reason: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "simulationId": simulation.id,
        "companyId": simulation.company_id,
        "terminatedByUserId": terminated_by_user_id,
    }
    if reason:
        payload["reason"] = reason
    return payload


async def enqueue_simulation_cleanup_job(
    db: AsyncSession,
    *,
    simulation: Simulation,
    terminated_by_user_id: int,
    reason: str | None,
    commit: bool = False,
) -> Job:
    payload = build_simulation_cleanup_payload(
        simulation,
        terminated_by_user_id=terminated_by_user_id,
        reason=reason,
    )
    return await jobs_repo.create_or_get_idempotent(
        db,
        job_type=SIMULATION_CLEANUP_JOB_TYPE,
        idempotency_key=simulation_cleanup_idempotency_key(simulation.id),
        payload_json=payload,
        company_id=simulation.company_id,
        max_attempts=SIMULATION_CLEANUP_MAX_ATTEMPTS,
        correlation_id=f"simulation:{simulation.id}:terminate",
        commit=commit,
    )


__all__ = [
    "SIMULATION_CLEANUP_JOB_TYPE",
    "build_simulation_cleanup_payload",
    "enqueue_simulation_cleanup_job",
    "simulation_cleanup_idempotency_key",
]
