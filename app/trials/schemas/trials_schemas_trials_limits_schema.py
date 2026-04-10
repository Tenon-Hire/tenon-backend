"""Application module for trials schemas trials limits schema workflows."""

from __future__ import annotations

import json
from typing import Any

from app.trials.constants.trials_constants_trials_ai_config_constants import (
    AI_EVAL_DAY_KEYS,
)

MAX_FOCUS_NOTES_CHARS = 1000
MAX_SCENARIO_STORYLINE_CHARS = 20_000
MAX_SCENARIO_NOTES_CHARS = 5_000
MAX_SCENARIO_TASK_PROMPTS_BYTES = 200 * 1024
MAX_SCENARIO_RUBRIC_BYTES = 200 * 1024
MAX_COMPANY_CONTEXT_VALUE_CHARS = 120
MAX_AI_NOTICE_VERSION_CHARS = 100
MAX_AI_NOTICE_TEXT_CHARS = 2000
_ALLOWED_ROLE_LEVELS = frozenset({"junior", "mid", "senior", "staff", "principal"})
_ALLOWED_AI_EVAL_DAY_KEYS = frozenset(AI_EVAL_DAY_KEYS)
_ALLOWED_DAY_WINDOW_OVERRIDE_KEYS = frozenset(str(day) for day in range(9, 22))


def _json_payload_size_bytes(value: Any) -> int:
    payload = json.dumps(
        value, separators=(",", ":"), ensure_ascii=False, sort_keys=True
    )
    return len(payload.encode("utf-8"))


def normalize_role_level(value: str | None) -> str | None:
    """Normalize role level."""
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized if normalized in _ALLOWED_ROLE_LEVELS else None


__all__ = [
    "MAX_AI_NOTICE_TEXT_CHARS",
    "MAX_AI_NOTICE_VERSION_CHARS",
    "MAX_COMPANY_CONTEXT_VALUE_CHARS",
    "MAX_FOCUS_NOTES_CHARS",
    "MAX_SCENARIO_NOTES_CHARS",
    "MAX_SCENARIO_RUBRIC_BYTES",
    "MAX_SCENARIO_STORYLINE_CHARS",
    "MAX_SCENARIO_TASK_PROMPTS_BYTES",
    "_ALLOWED_AI_EVAL_DAY_KEYS",
    "_ALLOWED_DAY_WINDOW_OVERRIDE_KEYS",
    "_ALLOWED_ROLE_LEVELS",
    "_json_payload_size_bytes",
    "normalize_role_level",
]
