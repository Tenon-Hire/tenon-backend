"""Application module for candidates candidate sessions repositories candidates candidate sessions day audits repository workflows."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import CandidateDayAudit


async def get_day_audit(
    db: AsyncSession, *, candidate_session_id: int, day_index: int
) -> CandidateDayAudit | None:
    """Return day audit."""
    stmt = select(CandidateDayAudit).where(
        CandidateDayAudit.candidate_session_id == candidate_session_id,
        CandidateDayAudit.day_index == day_index,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_day_audits(
    db: AsyncSession,
    *,
    candidate_session_ids: Iterable[int],
    day_indexes: Iterable[int] | None = None,
) -> list[CandidateDayAudit]:
    """Return day audits."""
    normalized_session_ids = sorted({int(value) for value in candidate_session_ids})
    if not normalized_session_ids:
        return []

    stmt = select(CandidateDayAudit).where(
        CandidateDayAudit.candidate_session_id.in_(normalized_session_ids)
    )
    if day_indexes is not None:
        normalized_day_indexes = sorted({int(value) for value in day_indexes})
        if not normalized_day_indexes:
            return []
        stmt = stmt.where(CandidateDayAudit.day_index.in_(normalized_day_indexes))

    stmt = stmt.order_by(
        CandidateDayAudit.candidate_session_id.asc(),
        CandidateDayAudit.day_index.asc(),
    )
    return (await db.execute(stmt)).scalars().all()


async def create_day_audit_once(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    day_index: int,
    cutoff_at: datetime,
    cutoff_commit_sha: str,
    eval_basis_ref: str,
    commit: bool = True,
) -> tuple[CandidateDayAudit, bool]:
    """Create day audit once."""
    existing = await get_day_audit(
        db,
        candidate_session_id=candidate_session_id,
        day_index=day_index,
    )
    if existing is not None:
        return existing, False

    audit = CandidateDayAudit(
        candidate_session_id=candidate_session_id,
        day_index=day_index,
        cutoff_at=cutoff_at,
        cutoff_commit_sha=cutoff_commit_sha,
        eval_basis_ref=eval_basis_ref,
    )
    db.add(audit)

    if commit:
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await get_day_audit(
                db,
                candidate_session_id=candidate_session_id,
                day_index=day_index,
            )
            if existing is None:
                raise
            return existing, False
        await db.refresh(audit)
        return audit, True

    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = await get_day_audit(
            db,
            candidate_session_id=candidate_session_id,
            day_index=day_index,
        )
        if existing is None:
            raise
        return existing, False
    return audit, True
