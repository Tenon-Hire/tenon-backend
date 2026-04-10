"""Constants for scenario_versions migration."""

DEFAULT_TEMPLATE_KEY = "python-fastapi"
TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME = "ck_trials_active_scenario_required"
TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_EXPR = (
    "status IN ('draft','generating') OR active_scenario_version_id IS NOT NULL"
)
