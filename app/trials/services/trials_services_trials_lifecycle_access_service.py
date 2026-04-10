"""Application module for trials services trials lifecycle access service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Trial


async def _load_for_lifecycle(
    db: AsyncSession, trial_id: int, *, for_update: bool
) -> Trial:
    stmt = select(Trial).where(Trial.id == trial_id)
    if for_update:
        stmt = stmt.with_for_update()
    trial = (await db.execute(stmt)).scalar_one_or_none()
    if trial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found"
        )
    return trial


async def require_owner_for_lifecycle(
    db: AsyncSession,
    trial_id: int,
    actor_user_id: int,
    *,
    for_update: bool = False,
) -> Trial:
    """Require owner for lifecycle."""
    trial = await _load_for_lifecycle(db, trial_id, for_update=for_update)
    if trial.created_by != actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trial",
        )
    return trial


__all__ = ["require_owner_for_lifecycle"]
