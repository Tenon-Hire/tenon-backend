"""Application module for downgrade workflows."""

from __future__ import annotations

from .constants import (
    EVALUATION_DAY_SCORES_TABLE,
    EVALUATION_RUNS_TABLE,
    IX_DAY_SCORES_RUN_ID,
    IX_RUNS_SESSION_SCENARIO,
    IX_RUNS_SESSION_STARTED_AT,
)


def run_downgrade(op) -> None:
    """Run downgrade."""
    op.drop_index(IX_DAY_SCORES_RUN_ID, table_name=EVALUATION_DAY_SCORES_TABLE)
    op.drop_table(EVALUATION_DAY_SCORES_TABLE)
    op.drop_index(IX_RUNS_SESSION_STARTED_AT, table_name=EVALUATION_RUNS_TABLE)
    op.drop_index(IX_RUNS_SESSION_SCENARIO, table_name=EVALUATION_RUNS_TABLE)
    op.drop_table(EVALUATION_RUNS_TABLE)
