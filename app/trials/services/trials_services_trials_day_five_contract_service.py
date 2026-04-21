"""Application module for trials services day five contract workflows."""

from __future__ import annotations

from typing import Any

from app.trials.constants.trials_constants_trials_blueprints_constants import (
    DEFAULT_5_DAY_DAY5_WINDOW_OVERRIDE,
)


def canonical_day_five_window_override() -> dict[str, dict[str, str]]:
    """Return the canonical Day 5 local schedule override."""
    return {
        day_index: dict(window)
        for day_index, window in DEFAULT_5_DAY_DAY5_WINDOW_OVERRIDE.items()
    }


def enforce_day_five_trial_contract(
    trial: Any,
    *,
    tasks: list[Any] | None = None,
) -> None:
    """Normalize the Day 5 trial contract before persistence."""
    trial.day_window_overrides_enabled = True
    trial.day_window_overrides_json = canonical_day_five_window_override()
    if tasks is None:
        return
    for task in tasks:
        if getattr(task, "day_index", None) == 5:
            task.type = "reflection"


__all__ = [
    "canonical_day_five_window_override",
    "enforce_day_five_trial_contract",
]
