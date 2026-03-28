"""Application module for simulations repositories simulations simulation status constants workflows."""

SIMULATION_STATUS_DRAFT = "draft"
SIMULATION_STATUS_GENERATING = "generating"
SIMULATION_STATUS_READY_FOR_REVIEW = "ready_for_review"
SIMULATION_STATUS_ACTIVE_INVITING = "active_inviting"
SIMULATION_STATUS_TERMINATED = "terminated"

SIMULATION_STATUSES = (
    SIMULATION_STATUS_DRAFT,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_TERMINATED,
)

LEGACY_SIMULATION_STATUS_ACTIVE = "active"
SIMULATION_STATUS_CHECK_CONSTRAINT_NAME = "ck_simulations_status_lifecycle"
SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME = (
    "ck_simulations_active_scenario_required"
)


def _status_check_expr() -> str:
    allowed = ",".join(f"'{status}'" for status in SIMULATION_STATUSES)
    return f"status IN ({allowed})"


def _active_scenario_required_expr() -> str:
    return "status IN ('draft','generating') OR active_scenario_version_id IS NOT NULL"
