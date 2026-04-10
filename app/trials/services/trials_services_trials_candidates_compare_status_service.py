"""Application module for trials services trials candidates compare status service workflows."""

from __future__ import annotations

from datetime import datetime

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_FAILED,
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
)
from app.trials.schemas.trials_schemas_trials_compare_schema import (
    CandidateCompareStatus,
    WinoeReportCompareStatus,
)
from app.trials.services.trials_services_trials_candidates_compare_constants import (
    COMPARE_DAYS,
)


def derive_winoe_report_status(
    *,
    has_ready_profile: bool,
    latest_run_status: str | None,
    has_active_job: bool,
) -> WinoeReportCompareStatus:
    """Derive winoe report status."""
    if has_ready_profile:
        return "ready"
    if latest_run_status in {
        EVALUATION_RUN_STATUS_PENDING,
        EVALUATION_RUN_STATUS_RUNNING,
    }:
        return "generating"
    if latest_run_status == EVALUATION_RUN_STATUS_FAILED:
        return "failed"
    return "generating" if has_active_job else "none"


def derive_candidate_compare_status(
    *,
    winoe_report_status: WinoeReportCompareStatus,
    day_completion: dict[str, bool],
    candidate_session_status: str | None,
    started_at: datetime | None,
    completed_at: datetime | None,
) -> CandidateCompareStatus:
    """Derive candidate compare status."""
    if winoe_report_status == "ready":
        return "evaluated"
    if (
        all(bool(day_completion.get(str(day), False)) for day in COMPARE_DAYS)
        or candidate_session_status == "completed"
        or completed_at is not None
    ):
        return "completed"
    has_progress = (
        any(bool(day_completion.get(str(day), False)) for day in COMPARE_DAYS)
        or candidate_session_status in {"in_progress", "completed"}
        or started_at is not None
        or completed_at is not None
    )
    return "in_progress" if has_progress else "scheduled"


__all__ = ["derive_candidate_compare_status", "derive_winoe_report_status"]
