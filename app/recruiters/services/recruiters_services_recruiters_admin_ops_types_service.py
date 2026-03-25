from __future__ import annotations

from dataclasses import dataclass

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


__all__ = [
    "UNSAFE_OPERATION_ERROR_CODE",
    "CANDIDATE_SESSION_RESET_ACTION",
    "JOB_REQUEUE_ACTION",
    "SIMULATION_USE_FALLBACK_ACTION",
    "CandidateSessionResetResult",
    "JobRequeueResult",
    "SimulationFallbackResult",
]
