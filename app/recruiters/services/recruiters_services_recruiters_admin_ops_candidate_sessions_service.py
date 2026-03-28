"""Application module for recruiters services recruiters admin ops candidate sessions service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.recruiters.services.recruiters_services_recruiters_admin_ops_audit_service import (
    insert_audit,
    log_admin_action,
    normalize_datetime,
    sanitized_reason,
    unsafe_operation,
)
from app.recruiters.services.recruiters_services_recruiters_admin_ops_candidate_helpers_service import (
    apply_model_updates,
    build_session_reset_fields,
    is_evaluated_candidate_session,
    load_candidate_session_for_update,
)
from app.recruiters.services.recruiters_services_recruiters_admin_ops_types_service import (
    CANDIDATE_SESSION_RESET_ACTION,
    CandidateSessionResetResult,
)
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils import (
    DemoAdminActor,
)


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
    """Reset candidate session."""
    resolved_now = normalize_datetime(now) or datetime.now(UTC)
    candidate_session = await load_candidate_session_for_update(
        db, candidate_session_id
    )
    evaluated = await is_evaluated_candidate_session(db, candidate_session_id)
    if evaluated and not override_if_evaluated:
        unsafe_operation(
            "Candidate session has completed evaluation runs.",
            details={
                "candidateSessionId": candidate_session_id,
                "overrideFlag": "overrideIfEvaluated",
            },
        )
    updates = build_session_reset_fields(
        candidate_session,
        target_state=target_state,
        now=resolved_now,
    )
    changed_fields = apply_model_updates(candidate_session, updates)
    if dry_run:
        await db.rollback()
        return CandidateSessionResetResult(
            candidate_session_id=candidate_session_id,
            reset_to=target_state,
            status="dry_run",
            audit_id=None,
        )
    audit_id = await insert_audit(
        db,
        actor=actor,
        action=CANDIDATE_SESSION_RESET_ACTION,
        target_type="candidate_session",
        target_id=candidate_session_id,
        payload={
            "reason": sanitized_reason(reason),
            "targetState": target_state,
            "overrideIfEvaluated": bool(override_if_evaluated),
            "noOp": not changed_fields,
            "changedFields": changed_fields,
            "evaluated": evaluated,
        },
    )
    await db.commit()
    log_admin_action(
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


__all__ = ["reset_candidate_session"]
