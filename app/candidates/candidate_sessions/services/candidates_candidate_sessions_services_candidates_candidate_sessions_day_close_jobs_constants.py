"""Application module for candidates candidate sessions services candidates candidate sessions day close jobs constants workflows."""

from __future__ import annotations

DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE = "day_close_finalize_text"
DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS = 8
DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES = {1, 5}
DAY_CLOSE_ENFORCEMENT_JOB_TYPE = "day_close_enforcement"
DAY_CLOSE_ENFORCEMENT_MAX_ATTEMPTS = 8
DAY_CLOSE_ENFORCEMENT_DAY_INDEXES = {2, 3}
DAY_CLOSE_ALL_DAY_INDEXES = (
    DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES | DAY_CLOSE_ENFORCEMENT_DAY_INDEXES
)


def day_close_finalize_text_idempotency_key(
    candidate_session_id: int, task_id: int
) -> str:
    """Execute day close finalize text idempotency key."""
    return f"day_close_finalize_text:{candidate_session_id}:{task_id}"


def day_close_enforcement_idempotency_key(
    candidate_session_id: int, day_index: int
) -> str:
    """Execute day close enforcement idempotency key."""
    return f"day_close_enforcement:{candidate_session_id}:{day_index}"


__all__ = [
    "DAY_CLOSE_ALL_DAY_INDEXES",
    "DAY_CLOSE_ENFORCEMENT_DAY_INDEXES",
    "DAY_CLOSE_ENFORCEMENT_JOB_TYPE",
    "DAY_CLOSE_ENFORCEMENT_MAX_ATTEMPTS",
    "DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES",
    "DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE",
    "DAY_CLOSE_FINALIZE_TEXT_MAX_ATTEMPTS",
    "day_close_enforcement_idempotency_key",
    "day_close_finalize_text_idempotency_key",
]
