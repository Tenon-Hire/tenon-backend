"""Application module for Talent Partners services Talent Partners admin ops trials service workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import build_ai_policy_snapshot
from app.shared.database.shared_database_models_model import Company, Task
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils import (
    DemoAdminActor,
)
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_audit_service import (
    insert_audit,
    log_admin_action,
    sanitized_reason,
)
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_trial_helpers_service import (
    assert_fallback_eligible,
    load_scenario_version_for_update,
    load_trial_for_update,
)
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_types_service import (
    TRIAL_USE_FALLBACK_ACTION,
    TrialFallbackResult,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
)
from app.trials.services.trials_services_trials_codespace_specializer_service import (
    ensure_precommit_bundle_prepared_for_approved_scenario,
)


async def _ensure_scenario_version_snapshot(
    db: AsyncSession,
    *,
    trial,
    scenario_version,
) -> None:
    if getattr(scenario_version, "ai_policy_snapshot_json", None):
        return
    company_prompt_overrides_json = await db.scalar(
        select(Company.ai_prompt_overrides_json).where(Company.id == trial.company_id)
    )
    scenario_version.ai_policy_snapshot_json = build_ai_policy_snapshot(
        trial=trial,
        company_prompt_overrides_json=company_prompt_overrides_json,
        trial_prompt_overrides_json=getattr(trial, "ai_prompt_overrides_json", None),
    )


async def use_trial_fallback_scenario(
    db: AsyncSession,
    *,
    actor: DemoAdminActor,
    trial_id: int,
    scenario_version_id: int,
    apply_to: str,
    reason: str,
    dry_run: bool,
) -> TrialFallbackResult:
    """Use trial fallback scenario."""
    trial = await load_trial_for_update(db, trial_id)
    scenario_version = await load_scenario_version_for_update(db, scenario_version_id)
    assert_fallback_eligible(
        trial=trial,
        scenario_version=scenario_version,
        trial_id=trial_id,
        scenario_version_id=scenario_version_id,
    )
    previous_active_scenario_version_id = trial.active_scenario_version_id
    no_op = previous_active_scenario_version_id == scenario_version.id
    resolved_scenario_version_id = scenario_version.id
    if not no_op:
        await _ensure_scenario_version_snapshot(
            db,
            trial=trial,
            scenario_version=scenario_version,
        )
        trial.active_scenario_version_id = resolved_scenario_version_id
        if trial.status == TRIAL_STATUS_ACTIVE_INVITING:
            tasks = (
                (
                    await db.execute(
                        select(Task)
                        .where(Task.trial_id == trial.id)
                        .order_by(Task.day_index.asc())
                    )
                )
                .scalars()
                .all()
            )
            await ensure_precommit_bundle_prepared_for_approved_scenario(
                db,
                trial=trial,
                scenario_version=scenario_version,
                tasks=tasks,
            )
    if dry_run:
        await db.rollback()
        return TrialFallbackResult(
            trial_id=trial_id,
            active_scenario_version_id=resolved_scenario_version_id,
            apply_to=apply_to,
            audit_id=None,
        )
    audit_id = await insert_audit(
        db,
        actor=actor,
        action=TRIAL_USE_FALLBACK_ACTION,
        target_type="trial",
        target_id=trial_id,
        payload={
            "reason": sanitized_reason(reason),
            "scenarioVersionId": scenario_version_id,
            "applyTo": apply_to,
            "noOp": no_op,
            "previousActiveScenarioVersionId": previous_active_scenario_version_id,
            "pendingScenarioVersionId": trial.pending_scenario_version_id,
        },
    )
    await db.commit()
    log_admin_action(
        audit_id=audit_id,
        action=TRIAL_USE_FALLBACK_ACTION,
        target_type="trial",
        target_id=trial_id,
        actor_id=actor.actor_id,
    )
    return TrialFallbackResult(
        trial_id=trial_id,
        active_scenario_version_id=resolved_scenario_version_id,
        apply_to=apply_to,
        audit_id=audit_id,
    )


__all__ = ["use_trial_fallback_scenario"]
