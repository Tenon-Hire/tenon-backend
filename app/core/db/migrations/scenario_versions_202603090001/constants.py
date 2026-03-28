"""Constants for scenario_versions migration."""

DEFAULT_TEMPLATE_KEY = "python-fastapi"
SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME = (
    "ck_simulations_active_scenario_required"
)
SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_EXPR = (
    "status IN ('draft','generating') OR active_scenario_version_id IS NOT NULL"
)
