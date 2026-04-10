"""Foreign key and index specs for reconciliation."""

from app.core.db.migrations.shared_trial_schema_compat import (
    resolve_pending_scenario_fk_name,
)


def build_fk_specs(
    parent_table_name: str,
) -> tuple[tuple[str, str, str, list[str], list[str]], ...]:
    return (
        (
            "fk_trials_active_scenario_version_id",
            parent_table_name,
            "scenario_versions",
            ["active_scenario_version_id"],
            ["id"],
        ),
        (
            resolve_pending_scenario_fk_name(parent_table_name),
            parent_table_name,
            "scenario_versions",
            ["pending_scenario_version_id"],
            ["id"],
        ),
        (
            "fk_candidate_sessions_scenario_version_id",
            "candidate_sessions",
            "scenario_versions",
            ["scenario_version_id"],
            ["id"],
        ),
        (
            "submissions_recording_id_fkey",
            "submissions",
            "recording_assets",
            ["recording_id"],
            ["id"],
        ),
        (
            "workspaces_workspace_group_id_fkey",
            "workspaces",
            "workspace_groups",
            ["workspace_group_id"],
            ["id"],
        ),
    )


FK_SPECS = build_fk_specs("trials")

INDEX_SPECS = (
    (
        "ix_candidate_sessions_scenario_version_id",
        "candidate_sessions",
        ["scenario_version_id"],
        False,
    ),
    ("ix_submissions_recording_id", "submissions", ["recording_id"], False),
)

WORKSPACES_GROUP_UNIQUE_NAME = "uq_workspaces_workspace_group_id"
