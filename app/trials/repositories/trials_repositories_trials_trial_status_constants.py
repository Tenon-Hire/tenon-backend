"""Application module for trials repositories trials trial status constants workflows."""

TRIAL_STATUS_DRAFT = "draft"
TRIAL_STATUS_GENERATING = "generating"
TRIAL_STATUS_READY_FOR_REVIEW = "ready_for_review"
TRIAL_STATUS_ACTIVE_INVITING = "active_inviting"
TRIAL_STATUS_TERMINATED = "terminated"

TRIAL_STATUSES = (
    TRIAL_STATUS_DRAFT,
    TRIAL_STATUS_GENERATING,
    TRIAL_STATUS_READY_FOR_REVIEW,
    TRIAL_STATUS_ACTIVE_INVITING,
    TRIAL_STATUS_TERMINATED,
)

LEGACY_TRIAL_STATUS_ACTIVE = "active"
TRIAL_STATUS_CHECK_CONSTRAINT_NAME = "ck_trials_status_lifecycle"
TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME = "ck_trials_active_scenario_required"


def _status_check_expr() -> str:
    allowed = ",".join(f"'{status}'" for status in TRIAL_STATUSES)
    return f"status IN ({allowed})"


def _active_scenario_required_expr() -> str:
    return "status IN ('draft','generating') OR active_scenario_version_id IS NOT NULL"
