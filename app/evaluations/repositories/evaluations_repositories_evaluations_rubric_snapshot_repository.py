"""Application module for evaluations repository rubric snapshot persistence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .evaluations_repositories_evaluations_rubric_snapshot_model import (
    WinoeRubricSnapshot,
)


async def list_rubric_snapshots_for_scenario_version(
    db: AsyncSession,
    *,
    scenario_version_id: int,
) -> list[WinoeRubricSnapshot]:
    stmt = (
        select(WinoeRubricSnapshot)
        .where(WinoeRubricSnapshot.scenario_version_id == scenario_version_id)
        .order_by(
            WinoeRubricSnapshot.scope.asc(),
            WinoeRubricSnapshot.rubric_kind.asc(),
            WinoeRubricSnapshot.rubric_key.asc(),
            WinoeRubricSnapshot.rubric_version.asc(),
            WinoeRubricSnapshot.id.asc(),
        )
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_rubric_snapshot_by_identity(
    db: AsyncSession,
    *,
    scenario_version_id: int,
    scope: str,
    rubric_kind: str,
    rubric_key: str,
    rubric_version: str,
) -> WinoeRubricSnapshot | None:
    stmt = select(WinoeRubricSnapshot).where(
        WinoeRubricSnapshot.scenario_version_id == scenario_version_id,
        WinoeRubricSnapshot.scope == scope,
        WinoeRubricSnapshot.rubric_kind == rubric_kind,
        WinoeRubricSnapshot.rubric_key == rubric_key,
        WinoeRubricSnapshot.rubric_version == rubric_version,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_rubric_snapshot(
    db: AsyncSession,
    *,
    scenario_version_id: int,
    scope: str,
    rubric_kind: str,
    rubric_key: str,
    rubric_version: str,
    content_hash: str,
    content_md: str,
    source_path: str | None = None,
    metadata_json: Mapping[str, Any] | None = None,
    commit: bool = False,
) -> WinoeRubricSnapshot:
    snapshot = WinoeRubricSnapshot(
        scenario_version_id=scenario_version_id,
        scope=scope,
        rubric_kind=rubric_kind,
        rubric_key=rubric_key,
        rubric_version=rubric_version,
        content_hash=content_hash,
        content_md=content_md,
        source_path=source_path,
        metadata_json=dict(metadata_json) if metadata_json is not None else None,
    )
    db.add(snapshot)
    if commit:
        await db.commit()
        await db.refresh(snapshot)
    else:
        await db.flush()
    return snapshot


__all__ = [
    "create_rubric_snapshot",
    "get_rubric_snapshot_by_identity",
    "list_rubric_snapshots_for_scenario_version",
]
