"""Application module for recruiters services recruiters admin ops simulations service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.recruiters.services.recruiters_services_recruiters_admin_ops_audit_service import (
    insert_audit,
    log_admin_action,
    sanitized_reason,
)
from app.recruiters.services.recruiters_services_recruiters_admin_ops_simulation_helpers_service import (
    assert_fallback_eligible,
    load_scenario_version_for_update,
    load_simulation_for_update,
)
from app.recruiters.services.recruiters_services_recruiters_admin_ops_types_service import (
    SIMULATION_USE_FALLBACK_ACTION,
    SimulationFallbackResult,
)
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils import (
    DemoAdminActor,
)


async def use_simulation_fallback_scenario(
    db: AsyncSession,
    *,
    actor: DemoAdminActor,
    simulation_id: int,
    scenario_version_id: int,
    apply_to: str,
    reason: str,
    dry_run: bool,
) -> SimulationFallbackResult:
    """Use simulation fallback scenario."""
    simulation = await load_simulation_for_update(db, simulation_id)
    scenario_version = await load_scenario_version_for_update(db, scenario_version_id)
    assert_fallback_eligible(
        simulation=simulation,
        scenario_version=scenario_version,
        simulation_id=simulation_id,
        scenario_version_id=scenario_version_id,
    )
    previous_active_scenario_version_id = simulation.active_scenario_version_id
    no_op = previous_active_scenario_version_id == scenario_version.id
    resolved_scenario_version_id = scenario_version.id
    if not no_op:
        simulation.active_scenario_version_id = resolved_scenario_version_id
    if dry_run:
        await db.rollback()
        return SimulationFallbackResult(
            simulation_id=simulation_id,
            active_scenario_version_id=resolved_scenario_version_id,
            apply_to=apply_to,
            audit_id=None,
        )
    audit_id = await insert_audit(
        db,
        actor=actor,
        action=SIMULATION_USE_FALLBACK_ACTION,
        target_type="simulation",
        target_id=simulation_id,
        payload={
            "reason": sanitized_reason(reason),
            "scenarioVersionId": scenario_version_id,
            "applyTo": apply_to,
            "noOp": no_op,
            "previousActiveScenarioVersionId": previous_active_scenario_version_id,
            "pendingScenarioVersionId": simulation.pending_scenario_version_id,
        },
    )
    await db.commit()
    log_admin_action(
        audit_id=audit_id,
        action=SIMULATION_USE_FALLBACK_ACTION,
        target_type="simulation",
        target_id=simulation_id,
        actor_id=actor.actor_id,
    )
    return SimulationFallbackResult(
        simulation_id=simulation_id,
        active_scenario_version_id=resolved_scenario_version_id,
        apply_to=apply_to,
        audit_id=audit_id,
    )


__all__ = ["use_simulation_fallback_scenario"]
