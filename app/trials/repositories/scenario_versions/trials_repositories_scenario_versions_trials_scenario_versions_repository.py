"""Application module for trials repositories scenario versions trials scenario versions repository workflows."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    ScenarioVersion,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    Trial,
)


async def get_by_id(
    db: AsyncSession, scenario_version_id: int, *, for_update: bool = False
) -> ScenarioVersion | None:
    """Return by id."""
    stmt = select(ScenarioVersion).where(ScenarioVersion.id == scenario_version_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_active_for_trial(
    db: AsyncSession,
    trial_id: int,
    *,
    for_update: bool = False,
) -> ScenarioVersion | None:
    """Return active for trial."""
    stmt = select(ScenarioVersion).join(
        Trial,
        Trial.active_scenario_version_id == ScenarioVersion.id,
    )
    stmt = stmt.where(Trial.id == trial_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def next_version_index(db: AsyncSession, trial_id: int) -> int:
    """Execute next version index."""
    max_idx = (
        await db.execute(
            select(func.max(ScenarioVersion.version_index)).where(
                ScenarioVersion.trial_id == trial_id
            )
        )
    ).scalar_one_or_none()
    return int(max_idx or 0) + 1


__all__ = ["get_by_id", "get_active_for_trial", "next_version_index"]
