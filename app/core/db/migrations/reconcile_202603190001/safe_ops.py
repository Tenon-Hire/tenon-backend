"""Idempotent schema operation wrappers."""

from __future__ import annotations

import sqlalchemy as sa

from .introspection import fk_names, has_column, index_names


def add_column_if_missing(
    op: object, bind: sa.Connection, table_name: str, column: sa.Column[object]
) -> None:
    """Add column if missing."""
    if not has_column(bind, table_name, column.name):
        op.add_column(table_name, column)


def add_fk_if_missing(
    op: object,
    bind: sa.Connection,
    *,
    name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    """Add fk if missing."""
    if name not in fk_names(bind, source_table):
        op.create_foreign_key(
            name, source_table, referent_table, local_cols, remote_cols
        )


def add_index_if_missing(
    op: object,
    bind: sa.Connection,
    *,
    name: str,
    table_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    """Add index if missing."""
    if name not in index_names(bind, table_name):
        op.create_index(name, table_name, columns, unique=unique)
