"""Application module for candidates candidate sessions services candidates candidate sessions day close jobs queries service workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Task


async def _load_tasks_for_day_indexes(
    db: AsyncSession, *, trial_id: int, day_indexes: set[int]
) -> list[Task]:
    return (
        (
            await db.execute(
                select(Task)
                .where(Task.trial_id == trial_id, Task.day_index.in_(day_indexes))
                .order_by(Task.day_index.asc(), Task.id.asc())
            )
        )
        .scalars()
        .all()
    )


__all__ = ["_load_tasks_for_day_indexes"]
