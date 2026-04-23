"""Application module for evaluations repositories evaluations constants model workflows."""

from __future__ import annotations

EVALUATION_RUN_STATUS_PENDING = "pending"
EVALUATION_RUN_STATUS_RUNNING = "running"
EVALUATION_RUN_STATUS_COMPLETED = "completed"
EVALUATION_RUN_STATUS_FAILED = "failed"
EVALUATION_RECOMMENDATION_HIRE = "hire"
EVALUATION_RECOMMENDATION_STRONG_HIRE = "strong_hire"
EVALUATION_RECOMMENDATION_NO_HIRE = "no_hire"
EVALUATION_RECOMMENDATION_LEAN_HIRE = "lean_hire"

EVALUATION_RUN_STATUSES = (
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
)
EVALUATION_RECOMMENDATIONS = (
    EVALUATION_RECOMMENDATION_HIRE,
    EVALUATION_RECOMMENDATION_STRONG_HIRE,
    EVALUATION_RECOMMENDATION_NO_HIRE,
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
)

EVALUATION_RUN_STATUS_CHECK_CONSTRAINT_NAME = "ck_evaluation_runs_status"
EVALUATION_RUN_COMPLETED_AT_CHECK_CONSTRAINT_NAME = (
    "ck_evaluation_runs_completed_after_started"
)
EVALUATION_RUN_RECOMMENDATION_CHECK_CONSTRAINT_NAME = (
    "ck_evaluation_runs_recommendation"
)
EVALUATION_DAY_SCORE_DAY_INDEX_CHECK_CONSTRAINT_NAME = (
    "ck_evaluation_day_scores_day_index"
)
EVALUATION_DAY_SCORE_RUN_DAY_UNIQUE_CONSTRAINT_NAME = "uq_evaluation_day_scores_run_day"
EVALUATION_REVIEWER_REPORT_DAY_INDEX_CHECK_CONSTRAINT_NAME = (
    "ck_evaluation_reviewer_reports_day_index"
)
EVALUATION_REVIEWER_REPORT_RUN_AGENT_DAY_UNIQUE_CONSTRAINT_NAME = (
    "uq_evaluation_reviewer_reports_run_agent_day"
)


def status_check_expr() -> str:
    """Execute status check expr."""
    allowed = ",".join(f"'{status}'" for status in EVALUATION_RUN_STATUSES)
    return f"status IN ({allowed})"


def recommendation_check_expr() -> str:
    """Execute recommendation check expr."""
    allowed = ",".join(f"'{value}'" for value in EVALUATION_RECOMMENDATIONS)
    return f"recommendation IS NULL OR recommendation IN ({allowed})"
