"""Foreign key and index specs for reconciliation."""

FK_SPECS = (
    (
        "fk_simulations_active_scenario_version_id",
        "simulations",
        "scenario_versions",
        ["active_scenario_version_id"],
        ["id"],
    ),
    (
        "fk_simulations_pending_scenario_version_id",
        "simulations",
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
