"""Application module for recruiters services recruiters admin ops candidate helpers service workflows."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
)
from app.recruiters.services.recruiters_services_recruiters_admin_ops_audit_service import (
    unsafe_operation,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    EvaluationRun,
)


async def load_candidate_session_for_update(
    db: AsyncSession, candidate_session_id: int
) -> CandidateSession:
    """Load candidate session for update."""
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


async def is_evaluated_candidate_session(
    db: AsyncSession, candidate_session_id: int
) -> bool:
    """Return whether evaluated candidate session."""
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


def build_session_reset_fields(
    candidate_session: CandidateSession,
    *,
    target_state: str,
    now: datetime,
) -> dict[str, object]:
    """Build session reset fields."""
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
    if target_state not in {"claimed", "in_progress"}:
        raise ValueError(f"Unsupported target_state: {target_state}")
    if not (candidate_session.candidate_auth0_sub or "").strip():
        unsafe_operation(
            "Cannot reset to a claimed state without an existing claimant identity.",
            details={"targetState": target_state, "requires": "candidate_auth0_sub"},
        )
    return {
        "status": "in_progress" if target_state == "in_progress" else "not_started",
        "claimed_at": candidate_session.claimed_at or now,
        "started_at": None
        if target_state == "claimed"
        else candidate_session.started_at or now,
        "completed_at": None,
        "scheduled_start_at": None,
        "candidate_timezone": None,
        "day_windows_json": None,
        "schedule_locked_at": None,
    }


def apply_model_updates(model: object, updates: dict[str, object]) -> list[str]:
    """Apply model updates."""
    changed_fields: list[str] = []
    for field_name, target_value in updates.items():
        current_value = getattr(model, field_name)
        if current_value != target_value:
            setattr(model, field_name, target_value)
            changed_fields.append(field_name)
    return changed_fields


__all__ = [
    "apply_model_updates",
    "build_session_reset_fields",
    "is_evaluated_candidate_session",
    "load_candidate_session_for_update",
]
