"""Application module for Talent Partners services Talent Partners admin ops types service workflows."""

from __future__ import annotations

from dataclasses import dataclass

UNSAFE_OPERATION_ERROR_CODE = "UNSAFE_OPERATION"
CANDIDATE_SESSION_RESET_ACTION = "candidate_session_reset"
CANDIDATE_SESSION_DAY_WINDOW_CONTROL_ACTION = "candidate_session_day_window_control"
JOB_REQUEUE_ACTION = "job_requeue"
TRIAL_USE_FALLBACK_ACTION = "trial_use_fallback"


@dataclass(frozen=True, slots=True)
class CandidateSessionResetResult:
    """Represent candidate session reset result data and behavior."""

    candidate_session_id: int
    reset_to: str
    status: str
    audit_id: str | None


@dataclass(frozen=True, slots=True)
class CandidateSessionDayWindowControlResult:
    """Represent candidate-session day-window control result data and behavior."""

    candidate_session_id: int
    candidate_status: str
    status: str
    target_day_index: int
    candidate_timezone: str
    scheduled_start_at: object
    schedule_locked_at: object
    day_windows: list[dict]
    current_day_window: dict | None
    audit_id: str | None


@dataclass(frozen=True, slots=True)
class JobRequeueResult:
    """Represent job requeue result data and behavior."""

    job_id: str
    previous_status: str
    new_status: str
    audit_id: str


@dataclass(frozen=True, slots=True)
class TrialFallbackResult:
    """Represent trial fallback result data and behavior."""

    trial_id: int
    active_scenario_version_id: int
    apply_to: str
    audit_id: str | None


__all__ = [
    "CANDIDATE_SESSION_DAY_WINDOW_CONTROL_ACTION",
    "UNSAFE_OPERATION_ERROR_CODE",
    "CANDIDATE_SESSION_RESET_ACTION",
    "JOB_REQUEUE_ACTION",
    "TRIAL_USE_FALLBACK_ACTION",
    "CandidateSessionDayWindowControlResult",
    "CandidateSessionResetResult",
    "JobRequeueResult",
    "TrialFallbackResult",
]
