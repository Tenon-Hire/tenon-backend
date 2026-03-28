"""Application module for submissions repositories submissions fit profile repository workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import FitProfile


async def get_by_candidate_session_id(
    db: AsyncSession,
    *,
    candidate_session_id: int,
) -> FitProfile | None:
    """Return by candidate session id."""
    stmt = select(FitProfile).where(
        FitProfile.candidate_session_id == candidate_session_id
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def upsert_marker(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    generated_at: datetime,
    commit: bool = True,
) -> FitProfile:
    """Upsert marker."""
    existing = await get_by_candidate_session_id(
        db,
        candidate_session_id=candidate_session_id,
    )
    if existing is None:
        marker = FitProfile(
            candidate_session_id=candidate_session_id,
            generated_at=generated_at,
        )
        db.add(marker)
    else:
        existing.generated_at = generated_at
        marker = existing

    if commit:
        await db.commit()
        await db.refresh(marker)
    else:
        await db.flush()
    return marker


__all__ = ["get_by_candidate_session_id", "upsert_marker"]
