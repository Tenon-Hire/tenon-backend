"""Application module for simulations constants simulations ai config constants workflows."""

from __future__ import annotations

from typing import Final

AI_NOTICE_DEFAULT_VERSION: Final[str] = "mvp1"
AI_NOTICE_DEFAULT_TEXT: Final[str] = (
    "We use AI to help evaluate submitted work artifacts, coding outputs, and "
    "communication signals across the simulation. Human reviewers oversee "
    "AI-generated findings and final hiring decisions are made by people."
)
AI_EVAL_DAY_KEYS: Final[tuple[str, str, str, str, str]] = ("1", "2", "3", "4", "5")
AI_EVAL_ENABLED_BY_DAY_DEFAULT_JSON: Final[
    str
] = '{"1": true, "2": true, "3": true, "4": true, "5": true}'


def default_ai_eval_enabled_by_day() -> dict[str, bool]:
    """Execute default ai eval enabled by day."""
    return {day: True for day in AI_EVAL_DAY_KEYS}


__all__ = [
    "AI_NOTICE_DEFAULT_VERSION",
    "AI_NOTICE_DEFAULT_TEXT",
    "AI_EVAL_DAY_KEYS",
    "AI_EVAL_ENABLED_BY_DAY_DEFAULT_JSON",
    "default_ai_eval_enabled_by_day",
]
