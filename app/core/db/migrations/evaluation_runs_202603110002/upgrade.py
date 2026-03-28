"""Application module for upgrade workflows."""

from __future__ import annotations

from .constants import (
    EVALUATION_DAY_SCORES_DAY_INDEX_CHECK,
    EVALUATION_DAY_SCORES_RUN_DAY_UNIQUE,
    EVALUATION_DAY_SCORES_TABLE,
    EVALUATION_RUNS_COMPLETED_AT_CHECK,
    EVALUATION_RUNS_STATUS_CHECK,
    EVALUATION_RUNS_TABLE,
    IX_DAY_SCORES_RUN_ID,
    IX_RUNS_SESSION_SCENARIO,
    IX_RUNS_SESSION_STARTED_AT,
)


def run_upgrade(op, sa) -> None:
    """Run upgrade."""
    _create_evaluation_runs(op, sa)
    _create_evaluation_day_scores(op, sa)


def _create_evaluation_runs(op, sa) -> None:
    op.create_table(
        EVALUATION_RUNS_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_session_id", sa.Integer(), nullable=False),
        sa.Column("scenario_version_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_version", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=255), nullable=False),
        sa.Column("rubric_version", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("day2_checkpoint_sha", sa.String(length=100), nullable=False),
        sa.Column("day3_final_sha", sa.String(length=100), nullable=False),
        sa.Column("cutoff_commit_sha", sa.String(length=100), nullable=False),
        sa.Column("transcript_reference", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','running','completed','failed')",
            name=EVALUATION_RUNS_STATUS_CHECK,
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name=EVALUATION_RUNS_COMPLETED_AT_CHECK,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_session_id"], ["candidate_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["scenario_version_id"], ["scenario_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        IX_RUNS_SESSION_SCENARIO,
        EVALUATION_RUNS_TABLE,
        ["candidate_session_id", "scenario_version_id"],
        unique=False,
    )
    op.create_index(
        IX_RUNS_SESSION_STARTED_AT,
        EVALUATION_RUNS_TABLE,
        ["candidate_session_id", "started_at"],
        unique=False,
    )


def _create_evaluation_day_scores(op, sa) -> None:
    op.create_table(
        EVALUATION_DAY_SCORES_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rubric_results_json", sa.JSON(), nullable=False),
        sa.Column("evidence_pointers_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "day_index BETWEEN 1 AND 5", name=EVALUATION_DAY_SCORES_DAY_INDEX_CHECK
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], [f"{EVALUATION_RUNS_TABLE}.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "day_index", name=EVALUATION_DAY_SCORES_RUN_DAY_UNIQUE
        ),
    )
    op.create_index(
        IX_DAY_SCORES_RUN_ID, EVALUATION_DAY_SCORES_TABLE, ["run_id"], unique=False
    )
