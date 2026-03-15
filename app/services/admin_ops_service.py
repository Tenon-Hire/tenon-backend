from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.admin_demo import DemoAdminActor
from app.core.errors import ApiError
from app.core.settings import settings
from app.domains import (
    CandidateSession,
    EvaluationRun,
    Job,
    ScenarioVersion,
    Simulation,
)
from app.repositories.admin_action_audits import repository as admin_audit_repo
from app.repositories.evaluations.models import EVALUATION_RUN_STATUS_COMPLETED
from app.repositories.jobs.models import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
)
from app.repositories.scenario_versions.models import (
    SCENARIO_VERSION_STATUS_LOCKED,
    SCENARIO_VERSION_STATUS_READY,
)
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED

logger = logging.getLogger(__name__)

UNSAFE_OPERATION_ERROR_CODE = "UNSAFE_OPERATION"
CANDIDATE_SESSION_RESET_ACTION = "candidate_session_reset"
JOB_REQUEUE_ACTION = "job_requeue"
SIMULATION_USE_FALLBACK_ACTION = "simulation_use_fallback"


@dataclass(frozen=True, slots=True)
class CandidateSessionResetResult:
    candidate_session_id: int
    reset_to: str
    status: str
    audit_id: str | None


@dataclass(frozen=True, slots=True)
class JobRequeueResult:
    job_id: str
    previous_status: str
    new_status: str
    audit_id: str


@dataclass(frozen=True, slots=True)
class SimulationFallbackResult:
    simulation_id: int
    active_scenario_version_id: int
    apply_to: str
    audit_id: str | None


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _unsafe_operation(detail: str, *, details: dict | None = None) -> None:
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
        error_code=UNSAFE_OPERATION_ERROR_CODE,
        retryable=False,
        details=details or {},
    )


def _sanitized_reason(reason: str) -> str:
    return " ".join((reason or "").split()).strip()


async def _insert_audit(
    db: AsyncSession,
    *,
    actor: DemoAdminActor,
    action: str,
    target_type: str,
    target_id: str | int,
    payload: dict,
) -> str:
    audit = await admin_audit_repo.create_audit(
        db,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload_json=payload,
        commit=False,
    )
    return audit.id


def _log_admin_action(
    *,
    audit_id: str,
    action: str,
    target_type: str,
    target_id: str | int,
    actor_id: str,
) -> None:
    logger.info(
        "admin_action_applied",
        extra={
            "audit_id": audit_id,
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "actor_id": actor_id,
        },
    )


async def _load_candidate_session_for_update(
    db: AsyncSession, candidate_session_id: int
) -> CandidateSession:
    candidate_session = (
        await db.execute(
            select(CandidateSession)
            .where(CandidateSession.id == candidate_session_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if candidate_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate session not found",
        )
    return candidate_session


async def _is_evaluated_candidate_session(
    db: AsyncSession, candidate_session_id: int
) -> bool:
    completed_run_id = (
        await db.execute(
            select(EvaluationRun.id)
            .where(
                EvaluationRun.candidate_session_id == candidate_session_id,
                EvaluationRun.status == EVALUATION_RUN_STATUS_COMPLETED,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return completed_run_id is not None


def _build_session_reset_fields(
    candidate_session: CandidateSession,
    *,
    target_state: str,
    now: datetime,
) -> dict[str, object]:
    if target_state == "not_started":
        return {
            "status": "not_started",
            "claimed_at": None,
            "candidate_auth0_sub": None,
            "candidate_email": None,
            "candidate_auth0_email": None,
            "started_at": None,
            "completed_at": None,
            "scheduled_start_at": None,
            "candidate_timezone": None,
            "day_windows_json": None,
            "schedule_locked_at": None,
            "github_username": None,
        }

    if target_state in {"claimed", "in_progress"}:
        if not (candidate_session.candidate_auth0_sub or "").strip():
            _unsafe_operation(
                "Cannot reset to a claimed state without an existing claimant identity.",
                details={
                    "targetState": target_state,
                    "requires": "candidate_auth0_sub",
                },
            )
        return {
            "status": "in_progress" if target_state == "in_progress" else "not_started",
            "claimed_at": candidate_session.claimed_at or now,
            "started_at": (
                None
                if target_state == "claimed"
                else candidate_session.started_at or now
            ),
            "completed_at": None,
            "scheduled_start_at": None,
            "candidate_timezone": None,
            "day_windows_json": None,
            "schedule_locked_at": None,
        }

    raise ValueError(f"Unsupported target_state: {target_state}")


def _apply_model_updates(model: object, updates: dict[str, object]) -> list[str]:
    changed_fields: list[str] = []
    for field_name, target_value in updates.items():
        current_value = getattr(model, field_name)
        if current_value != target_value:
            setattr(model, field_name, target_value)
            changed_fields.append(field_name)
    return changed_fields


async def reset_candidate_session(
    db: AsyncSession,
    *,
    actor: DemoAdminActor,
    candidate_session_id: int,
    target_state: str,
    reason: str,
    override_if_evaluated: bool,
    dry_run: bool,
    now: datetime | None = None,
) -> CandidateSessionResetResult:
    resolved_now = _normalize_datetime(now) or datetime.now(UTC)
    candidate_session = await _load_candidate_session_for_update(
        db, candidate_session_id
    )
    evaluated = await _is_evaluated_candidate_session(db, candidate_session_id)
    if evaluated and not override_if_evaluated:
        _unsafe_operation(
            "Candidate session has completed evaluation runs.",
            details={
                "candidateSessionId": candidate_session_id,
                "overrideFlag": "overrideIfEvaluated",
            },
        )

    updates = _build_session_reset_fields(
        candidate_session,
        target_state=target_state,
        now=resolved_now,
    )
    changed_fields = _apply_model_updates(candidate_session, updates)
    no_op = not changed_fields

    if dry_run:
        await db.rollback()
        return CandidateSessionResetResult(
            candidate_session_id=candidate_session_id,
            reset_to=target_state,
            status="dry_run",
            audit_id=None,
        )

    audit_id = await _insert_audit(
        db,
        actor=actor,
        action=CANDIDATE_SESSION_RESET_ACTION,
        target_type="candidate_session",
        target_id=candidate_session_id,
        payload={
            "reason": _sanitized_reason(reason),
            "targetState": target_state,
            "overrideIfEvaluated": bool(override_if_evaluated),
            "noOp": no_op,
            "changedFields": changed_fields,
            "evaluated": evaluated,
        },
    )
    await db.commit()
    _log_admin_action(
        audit_id=audit_id,
        action=CANDIDATE_SESSION_RESET_ACTION,
        target_type="candidate_session",
        target_id=candidate_session_id,
        actor_id=actor.actor_id,
    )
    return CandidateSessionResetResult(
        candidate_session_id=candidate_session_id,
        reset_to=target_state,
        status="ok",
        audit_id=audit_id,
    )


async def _load_job_for_update(db: AsyncSession, job_id: str) -> Job:
    job = (
        await db.execute(select(Job).where(Job.id == job_id).with_for_update())
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return job


def _job_stale_seconds() -> int:
    configured = int(settings.DEMO_ADMIN_JOB_STALE_SECONDS or 0)
    return configured if configured > 0 else 900


def _is_stale_running_job(job: Job, *, now: datetime) -> bool:
    if job.status != JOB_STATUS_RUNNING:
        return False
    locked_at = _normalize_datetime(job.locked_at)
    if locked_at is None:
        return True
    stale_before = now - timedelta(seconds=_job_stale_seconds())
    return locked_at <= stale_before


async def requeue_job(
    db: AsyncSession,
    *,
    actor: DemoAdminActor,
    job_id: str,
    reason: str,
    force: bool,
    now: datetime | None = None,
) -> JobRequeueResult:
    resolved_now = _normalize_datetime(now) or datetime.now(UTC)
    job = await _load_job_for_update(db, job_id)
    previous_status = job.status
    stale_running = _is_stale_running_job(job, now=resolved_now)
    no_op = job.status == JOB_STATUS_QUEUED

    if not no_op:
        if not force:
            if job.status == JOB_STATUS_DEAD_LETTER or stale_running:
                pass
            else:
                _unsafe_operation(
                    "Job cannot be requeued without force from its current status.",
                    details={
                        "jobId": job_id,
                        "status": job.status,
                        "staleRunningThresholdSeconds": _job_stale_seconds(),
                    },
                )
        elif job.status not in {
            JOB_STATUS_RUNNING,
            JOB_STATUS_DEAD_LETTER,
            JOB_STATUS_SUCCEEDED,
        }:
            _unsafe_operation(
                "Job cannot be force requeued from its current status.",
                details={"jobId": job_id, "status": job.status},
            )

    if not no_op:
        job.status = JOB_STATUS_QUEUED
        job.next_run_at = resolved_now
        job.locked_at = None
        job.locked_by = None
        job.last_error = None
        job.result_json = None

    audit_id = await _insert_audit(
        db,
        actor=actor,
        action=JOB_REQUEUE_ACTION,
        target_type="job",
        target_id=job_id,
        payload={
            "reason": _sanitized_reason(reason),
            "force": bool(force),
            "previousStatus": previous_status,
            "newStatus": job.status,
            "noOp": no_op,
            "staleRunning": stale_running,
            "staleRunningThresholdSeconds": _job_stale_seconds(),
        },
    )
    await db.commit()
    _log_admin_action(
        audit_id=audit_id,
        action=JOB_REQUEUE_ACTION,
        target_type="job",
        target_id=job_id,
        actor_id=actor.actor_id,
    )
    return JobRequeueResult(
        job_id=job.id,
        previous_status=previous_status,
        new_status=job.status,
        audit_id=audit_id,
    )


async def _load_simulation_for_update(
    db: AsyncSession, simulation_id: int
) -> Simulation:
    simulation = (
        await db.execute(
            select(Simulation).where(Simulation.id == simulation_id).with_for_update()
        )
    ).scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )
    return simulation


async def _load_scenario_version_for_update(
    db: AsyncSession, scenario_version_id: int
) -> ScenarioVersion:
    scenario_version = (
        await db.execute(
            select(ScenarioVersion)
            .where(ScenarioVersion.id == scenario_version_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if scenario_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario version not found",
        )
    return scenario_version


async def use_simulation_fallback_scenario(
    db: AsyncSession,
    *,
    actor: DemoAdminActor,
    simulation_id: int,
    scenario_version_id: int,
    apply_to: str,
    reason: str,
    dry_run: bool,
) -> SimulationFallbackResult:
    simulation = await _load_simulation_for_update(db, simulation_id)
    if simulation.status == SIMULATION_STATUS_TERMINATED:
        _unsafe_operation(
            "Cannot switch fallback scenario for a terminated simulation.",
            details={"simulationId": simulation_id, "status": simulation.status},
        )

    scenario_version = await _load_scenario_version_for_update(db, scenario_version_id)
    if scenario_version.simulation_id != simulation.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario version not found",
        )
    if scenario_version.status not in {
        SCENARIO_VERSION_STATUS_READY,
        SCENARIO_VERSION_STATUS_LOCKED,
    }:
        _unsafe_operation(
            "Scenario version is not eligible as a fallback.",
            details={
                "simulationId": simulation_id,
                "scenarioVersionId": scenario_version_id,
                "status": scenario_version.status,
            },
        )
    if simulation.pending_scenario_version_id is not None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario approval is pending before inviting.",
            error_code="SCENARIO_APPROVAL_PENDING",
            retryable=False,
            details={
                "pendingScenarioVersionId": simulation.pending_scenario_version_id
            },
        )

    previous_active_scenario_version_id = simulation.active_scenario_version_id
    no_op = previous_active_scenario_version_id == scenario_version.id
    resolved_scenario_version_id = scenario_version.id
    if not no_op:
        simulation.active_scenario_version_id = resolved_scenario_version_id

    if dry_run:
        await db.rollback()
        return SimulationFallbackResult(
            simulation_id=simulation_id,
            active_scenario_version_id=resolved_scenario_version_id,
            apply_to=apply_to,
            audit_id=None,
        )

    audit_id = await _insert_audit(
        db,
        actor=actor,
        action=SIMULATION_USE_FALLBACK_ACTION,
        target_type="simulation",
        target_id=simulation_id,
        payload={
            "reason": _sanitized_reason(reason),
            "scenarioVersionId": scenario_version_id,
            "applyTo": apply_to,
            "noOp": no_op,
            "previousActiveScenarioVersionId": previous_active_scenario_version_id,
            "pendingScenarioVersionId": simulation.pending_scenario_version_id,
        },
    )
    await db.commit()
    _log_admin_action(
        audit_id=audit_id,
        action=SIMULATION_USE_FALLBACK_ACTION,
        target_type="simulation",
        target_id=simulation_id,
        actor_id=actor.actor_id,
    )
    return SimulationFallbackResult(
        simulation_id=simulation_id,
        active_scenario_version_id=resolved_scenario_version_id,
        apply_to=apply_to,
        audit_id=audit_id,
    )


__all__ = [
    "CandidateSessionResetResult",
    "JobRequeueResult",
    "SimulationFallbackResult",
    "reset_candidate_session",
    "requeue_job",
    "use_simulation_fallback_scenario",
]
