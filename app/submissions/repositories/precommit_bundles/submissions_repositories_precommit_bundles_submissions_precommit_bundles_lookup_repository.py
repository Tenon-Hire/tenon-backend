"""Application module for submissions repositories precommit bundles submissions precommit bundles lookup repository workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories.precommit_bundles.submissions_repositories_precommit_bundles_submissions_precommit_bundles_core_model import (
    PRECOMMIT_BUNDLE_STATUS_READY,
    PrecommitBundle,
)

from .submissions_repositories_precommit_bundles_submissions_precommit_bundles_validations_repository import (
    normalize_template_key,
)


async def get_by_scenario_and_template(
    db: AsyncSession,
    *,
    scenario_version_id: int,
    template_key: str,
) -> PrecommitBundle | None:
    """Return by scenario and template."""
    stmt = select(PrecommitBundle).where(
        PrecommitBundle.scenario_version_id == scenario_version_id,
        PrecommitBundle.template_key == normalize_template_key(template_key),
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_ready_by_scenario_and_template(
    db: AsyncSession,
    *,
    scenario_version_id: int,
    template_key: str,
) -> PrecommitBundle | None:
    """Return ready by scenario and template."""
    stmt = select(PrecommitBundle).where(
        PrecommitBundle.scenario_version_id == scenario_version_id,
        PrecommitBundle.template_key == normalize_template_key(template_key),
        PrecommitBundle.status == PRECOMMIT_BUNDLE_STATUS_READY,
    )
    return (await db.execute(stmt)).scalar_one_or_none()
