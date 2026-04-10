"""Upgrade runner for revision 202603190001."""

from __future__ import annotations

import sqlalchemy as sa

from app.core.db.migrations.shared_trial_schema_compat import (
    resolve_trial_parent_table_name,
)

from .introspection import index_names, unique_constraint_names
from .recording_status import reconcile_recording_status_check
from .safe_ops import add_column_if_missing, add_fk_if_missing, add_index_if_missing
from .scenario_backfill import ensure_scenario_versions_backfill
from .specs_columns import build_column_specs
from .specs_constraints import (
    INDEX_SPECS,
    WORKSPACES_GROUP_UNIQUE_NAME,
    build_fk_specs,
)


def run_upgrade(op: object, bind: sa.Connection) -> None:
    """Run upgrade."""
    parent_table_name = resolve_trial_parent_table_name(bind)
    column_specs = build_column_specs(parent_table_name)
    fk_specs = build_fk_specs(parent_table_name)

    for table_name, name, type_ in column_specs:
        add_column_if_missing(
            op, bind, table_name, sa.Column(name, type_, nullable=True)
        )

    ensure_scenario_versions_backfill(bind)

    for name, source_table, referent_table, local_cols, remote_cols in fk_specs:
        add_fk_if_missing(
            op,
            bind,
            name=name,
            source_table=source_table,
            referent_table=referent_table,
            local_cols=list(local_cols),
            remote_cols=list(remote_cols),
        )

    for name, table_name, columns, unique in INDEX_SPECS:
        add_index_if_missing(
            op,
            bind,
            name=name,
            table_name=table_name,
            columns=list(columns),
            unique=unique,
        )

    unique_names = unique_constraint_names(bind, "workspaces")
    workspace_index_names = index_names(bind, "workspaces")
    if (
        WORKSPACES_GROUP_UNIQUE_NAME not in unique_names
        and WORKSPACES_GROUP_UNIQUE_NAME not in workspace_index_names
    ):
        op.create_unique_constraint(
            WORKSPACES_GROUP_UNIQUE_NAME, "workspaces", ["workspace_group_id"]
        )

    reconcile_recording_status_check(op, bind)
