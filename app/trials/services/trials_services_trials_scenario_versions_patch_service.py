"""Application module for trials services trials scenario versions patch service workflows."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    ScenarioEditAudit,
    ScenarioVersion,
    Trial,
)
from app.trials.repositories.scenario_versions import (
    trials_repositories_scenario_versions_trials_scenario_versions_repository as scenario_repo,
)
from app.trials.services.trials_services_trials_scenario_versions_access_service import (
    require_owned_trial_for_update,
)
from app.trials.services.trials_services_trials_scenario_versions_constants import (
    SCENARIO_PATCH_FIELD_ORDER,
)
from app.trials.services.trials_services_trials_scenario_versions_patch_utils_service import (
    apply_normalized_patch,
    ensure_patch_allowed,
    merge_patch_state,
    snapshot_editable_state,
)
from app.trials.services.trials_services_trials_scenario_versions_patching_service import (
    build_edit_audit_payload,
    validate_and_normalize_merged_scenario_state,
)

logger = logging.getLogger(__name__)


async def patch_scenario_version(
    db: AsyncSession,
    *,
    trial_id: int,
    scenario_version_id: int,
    actor_user_id: int,
    updates: dict[str, Any],
) -> ScenarioVersion:
    """Patch scenario version."""
    trial = await require_owned_trial_for_update(db, trial_id, actor_user_id)
    scenario_version = await _require_scenario_for_patch(db, scenario_version_id, trial)
    ensure_patch_allowed(trial, scenario_version, actor_user_id)
    before_state = snapshot_editable_state(scenario_version)
    candidate_fields = [
        field for field in SCENARIO_PATCH_FIELD_ORDER if field in updates
    ]
    merged_state = merge_patch_state(before_state, updates, candidate_fields)
    normalized_state = validate_and_normalize_merged_scenario_state(merged_state)
    apply_normalized_patch(scenario_version, normalized_state)
    db.add(
        ScenarioEditAudit(
            scenario_version_id=scenario_version.id,
            talent_partner_id=actor_user_id,
            patch_json=build_edit_audit_payload(
                before=before_state,
                after=normalized_state,
                candidate_fields=candidate_fields,
            ),
        )
    )
    await db.commit()
    await db.refresh(scenario_version)
    logger.info(
        "Scenario patch applied trialId=%s scenarioVersionId=%s talentPartnerId=%s",
        trial.id,
        scenario_version.id,
        actor_user_id,
    )
    return scenario_version


async def _require_scenario_for_patch(
    db: AsyncSession, scenario_version_id: int, trial: Trial
) -> ScenarioVersion:
    scenario_version = await scenario_repo.get_by_id(
        db, scenario_version_id, for_update=True
    )
    if scenario_version is None or scenario_version.trial_id != trial.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scenario version not found"
        )
    return scenario_version
