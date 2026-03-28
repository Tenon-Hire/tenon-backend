"""Schema inspection helpers."""

from __future__ import annotations

import sqlalchemy as sa


def column_names(bind: sa.Connection, table_name: str) -> set[str]:
    """Execute column names."""
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def has_column(bind: sa.Connection, table_name: str, column_name: str) -> bool:
    """Execute has column."""
    return column_name in column_names(bind, table_name)


def fk_names(bind: sa.Connection, table_name: str) -> set[str]:
    """Execute fk names."""
    inspector = sa.inspect(bind)
    return {
        fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")
    }


def index_names(bind: sa.Connection, table_name: str) -> set[str]:
    """Execute index names."""
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name) if idx.get("name")}


def check_names(bind: sa.Connection, table_name: str) -> set[str]:
    """Check names."""
    inspector = sa.inspect(bind)
    checks = inspector.get_check_constraints(table_name) or []
    return {check["name"] for check in checks if check.get("name")}


def table_exists(bind: sa.Connection, table_name: str) -> bool:
    """Execute table exists."""
    return table_name in set(sa.inspect(bind).get_table_names())


def unique_constraint_names(bind: sa.Connection, table_name: str) -> set[str]:
    """Execute unique constraint names."""
    return {
        item["name"]
        for item in sa.inspect(bind).get_unique_constraints(table_name)
        if item.get("name")
    }
