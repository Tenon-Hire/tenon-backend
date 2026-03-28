"""Application module for downgrade workflows."""

from __future__ import annotations

from .constants import (
    IX_RECORDING_ASSETS_SESSION_ID,
    IX_RECORDING_ASSETS_SESSION_TASK_CREATED,
    IX_RECORDING_ASSETS_TASK_ID,
    IX_TRANSCRIPTS_RECORDING_ID,
    IX_TRANSCRIPTS_STATUS_CREATED_AT,
    RECORDING_ASSETS_TABLE,
    TRANSCRIPTS_TABLE,
)


def run_downgrade(op) -> None:
    """Run downgrade."""
    op.drop_index(IX_TRANSCRIPTS_STATUS_CREATED_AT, table_name=TRANSCRIPTS_TABLE)
    op.drop_index(IX_TRANSCRIPTS_RECORDING_ID, table_name=TRANSCRIPTS_TABLE)
    op.drop_table(TRANSCRIPTS_TABLE)
    op.drop_index(IX_RECORDING_ASSETS_TASK_ID, table_name=RECORDING_ASSETS_TABLE)
    op.drop_index(IX_RECORDING_ASSETS_SESSION_ID, table_name=RECORDING_ASSETS_TABLE)
    op.drop_index(
        IX_RECORDING_ASSETS_SESSION_TASK_CREATED, table_name=RECORDING_ASSETS_TABLE
    )
    op.drop_table(RECORDING_ASSETS_TABLE)
