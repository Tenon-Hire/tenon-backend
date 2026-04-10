"""Compatibility helpers for legacy `simulations` and current `trials` schema names."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.engine import Connection

_TRIAL_PARENT_TABLE_CANDIDATES = ("trials", "simulations")
_CANDIDATE_SESSION_PARENT_COLUMN_CANDIDATES = ("trial_id", "simulation_id")


def _inspector(bind: Connection) -> sa.Inspector | None:
    try:
        return sa.inspect(bind)
    except sa.exc.NoInspectionAvailable:
        return None


def _table_names(bind: Connection) -> set[str]:
    inspector = _inspector(bind)
    if inspector is None:
        return set()
    return set(inspector.get_table_names())


def resolve_trial_parent_table_name(bind: Connection) -> str:
    """Return the active parent table for trials/simulations."""
    table_names = _table_names(bind)
    for candidate in _TRIAL_PARENT_TABLE_CANDIDATES:
        if candidate in table_names:
            return candidate
    return "trials"


def resolve_candidate_session_parent_column_name(bind: Connection) -> str:
    """Return the candidate-session foreign-key column for the parent table."""
    if "candidate_sessions" not in _table_names(bind):
        return "trial_id"

    inspector = _inspector(bind)
    if inspector is None:
        return "trial_id"
    columns = {column["name"] for column in inspector.get_columns("candidate_sessions")}
    for candidate in _CANDIDATE_SESSION_PARENT_COLUMN_CANDIDATES:
        if candidate in columns:
            return candidate
    return "trial_id"


def resolve_pending_scenario_fk_name(parent_table_name: str) -> str:
    """Return the canonical pending-scenario FK name for the active schema."""
    if parent_table_name == "simulations":
        return "fk_simulations_pending_scenario_version_id"
    return "fk_trials_pending_scenario_version_id"
