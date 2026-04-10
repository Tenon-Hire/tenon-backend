"""Application module for trials services trials ownership service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Task, Trial


async def require_owned_trial(
    db: AsyncSession,
    trial_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
    for_update: bool = False,
) -> Trial:
    """Require owned trial."""
    from app.trials import services as sim_service

    sim = await sim_service.sim_repo.get_owned(
        db,
        trial_id,
        user_id,
        include_terminated=include_terminated,
        for_update=for_update,
    )
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found"
        )
    return sim


async def require_owned_trial_with_tasks(
    db: AsyncSession,
    trial_id: int,
    user_id: int,
    *,
    include_terminated: bool = True,
    for_update: bool = False,
) -> tuple[Trial, list[Task]]:
    """Require owned trial with tasks."""
    from app.trials import services as sim_service

    sim, tasks = await sim_service.sim_repo.get_owned_with_tasks(
        db,
        trial_id,
        user_id,
        include_terminated=include_terminated,
        for_update=for_update,
    )
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found"
        )
    return sim, tasks
