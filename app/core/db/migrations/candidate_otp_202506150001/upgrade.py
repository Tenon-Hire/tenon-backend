"""Application module for upgrade workflows."""

from __future__ import annotations

from .constants import DROP_COLUMNS, DROP_INDEXES, TABLE_NAME


def run_upgrade(op, sa) -> None:
    """Run upgrade."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns(TABLE_NAME)}
    indexes = {idx["name"] for idx in inspector.get_indexes(TABLE_NAME)}

    for index_name in DROP_INDEXES:
        if index_name in indexes:
            op.drop_index(index_name, table_name=TABLE_NAME)

    for column_name in DROP_COLUMNS:
        if column_name in columns:
            op.drop_column(TABLE_NAME, column_name)
