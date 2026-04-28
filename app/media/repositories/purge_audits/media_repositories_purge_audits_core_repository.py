"""Repository helpers for media purge audit records."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.media.repositories.purge_audits.media_repositories_purge_audits_core_model import (
    MediaPurgeAudit,
)


async def create_audit(
    db: AsyncSession,
    *,
    media_id: int,
    candidate_session_id: int | None,
    trial_id: int | None,
    candidate_user_id: int | None,
    actor_type: str,
    actor_id: str | None,
    purge_reason: str,
    outcome: str,
    error_summary: str | None = None,
    commit: bool = False,
) -> MediaPurgeAudit:
    """Create a media purge audit record."""
    audit = MediaPurgeAudit(
        media_id=media_id,
        candidate_session_id=candidate_session_id,
        trial_id=trial_id,
        candidate_user_id=candidate_user_id,
        actor_type=actor_type,
        actor_id=actor_id,
        purge_reason=purge_reason,
        outcome=outcome,
        error_summary=error_summary,
    )
    db.add(audit)
    if commit:
        await db.commit()
        await db.refresh(audit)
    else:
        await db.flush()
    return audit


__all__ = ["create_audit"]
