"""Column specifications for reconciliation."""

from __future__ import annotations

import sqlalchemy as sa


def build_column_specs(
    parent_table_name: str,
) -> tuple[tuple[str, str, sa.TypeEngine[object]], ...]:
    return (
        (parent_table_name, "active_scenario_version_id", sa.Integer()),
        (parent_table_name, "pending_scenario_version_id", sa.Integer()),
        ("candidate_sessions", "scenario_version_id", sa.Integer()),
        ("candidate_sessions", "consent_version", sa.String(length=100)),
        ("candidate_sessions", "consent_timestamp", sa.DateTime(timezone=True)),
        ("candidate_sessions", "ai_notice_version", sa.String(length=100)),
        ("recording_assets", "deleted_at", sa.DateTime(timezone=True)),
        ("recording_assets", "purged_at", sa.DateTime(timezone=True)),
        ("recording_assets", "consent_version", sa.String(length=100)),
        ("recording_assets", "consent_timestamp", sa.DateTime(timezone=True)),
        ("recording_assets", "ai_notice_version", sa.String(length=100)),
        ("submissions", "recording_id", sa.Integer()),
        ("submissions", "checkpoint_sha", sa.String(length=100)),
        ("submissions", "final_sha", sa.String(length=100)),
        ("submissions", "workflow_run_attempt", sa.Integer()),
        ("submissions", "workflow_run_status", sa.String(length=50)),
        ("submissions", "workflow_run_conclusion", sa.String(length=50)),
        ("submissions", "workflow_run_completed_at", sa.DateTime(timezone=True)),
        ("transcripts", "deleted_at", sa.DateTime(timezone=True)),
        ("workspace_groups", "cleanup_status", sa.String(length=20)),
        ("workspace_groups", "cleanup_attempted_at", sa.DateTime(timezone=True)),
        ("workspace_groups", "cleaned_at", sa.DateTime(timezone=True)),
        ("workspace_groups", "cleanup_error", sa.Text()),
        ("workspace_groups", "retention_expires_at", sa.DateTime(timezone=True)),
        ("workspace_groups", "access_revoked_at", sa.DateTime(timezone=True)),
        ("workspace_groups", "access_revocation_error", sa.Text()),
        ("workspaces", "workspace_group_id", sa.String(length=36)),
        ("workspaces", "precommit_sha", sa.String(length=100)),
        ("workspaces", "precommit_details_json", sa.Text()),
        ("workspaces", "cleanup_status", sa.String(length=20)),
        ("workspaces", "cleanup_attempted_at", sa.DateTime(timezone=True)),
        ("workspaces", "cleaned_at", sa.DateTime(timezone=True)),
        ("workspaces", "cleanup_error", sa.Text()),
        ("workspaces", "retention_expires_at", sa.DateTime(timezone=True)),
        ("workspaces", "access_revoked_at", sa.DateTime(timezone=True)),
        ("workspaces", "access_revocation_error", sa.Text()),
    )


COLUMN_SPECS = build_column_specs("trials")
