from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa

from alembic.migration import MigrationContext
from alembic.operations import Operations

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[4]
    / "alembic/versions/202604140001_add_worker_heartbeats_table.py"
)
_MIGRATION_SPEC = importlib.util.spec_from_file_location(
    "worker_heartbeats_migration", _MIGRATION_PATH
)
assert _MIGRATION_SPEC and _MIGRATION_SPEC.loader
worker_heartbeats_migration = importlib.util.module_from_spec(_MIGRATION_SPEC)
_MIGRATION_SPEC.loader.exec_module(worker_heartbeats_migration)


def _operations(bind: sa.Connection) -> Operations:
    return Operations(MigrationContext.configure(bind))


def test_worker_heartbeats_migration_upgrade_and_downgrade() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        worker_heartbeats_migration.op = _operations(conn)
        worker_heartbeats_migration.upgrade()

        inspector = sa.inspect(conn)
        assert "worker_heartbeats" in inspector.get_table_names()
        column_names = {
            column["name"] for column in inspector.get_columns("worker_heartbeats")
        }
        assert column_names == {
            "service_name",
            "instance_id",
            "status",
            "started_at",
            "last_heartbeat_at",
            "created_at",
            "updated_at",
        }
        index_names = {
            index["name"]
            for index in inspector.get_indexes("worker_heartbeats")
            if index.get("name")
        }
        assert "ix_worker_heartbeats_service_last_heartbeat" in index_names

        worker_heartbeats_migration.downgrade()
        assert "worker_heartbeats" not in sa.inspect(conn).get_table_names()


def test_worker_heartbeats_migration_upgrade_backfills_index_when_table_exists() -> (
    None
):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "worker_heartbeats",
        metadata,
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("instance_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("service_name", "instance_id"),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        worker_heartbeats_migration.op = _operations(conn)
        worker_heartbeats_migration.upgrade()

        index_names = {
            index["name"]
            for index in sa.inspect(conn).get_indexes("worker_heartbeats")
            if index.get("name")
        }
        assert "ix_worker_heartbeats_service_last_heartbeat" in index_names


@pytest.mark.parametrize(
    ("table_columns", "expected_error"),
    [
        (
            [
                sa.Column("service_name", sa.String(length=100), nullable=False),
                sa.Column("instance_id", sa.String(length=255), nullable=False),
                sa.Column("status", sa.String(length=32), nullable=False),
                sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
                sa.PrimaryKeyConstraint("service_name", "instance_id"),
            ],
            "missing_columns",
        ),
        (
            [
                sa.Column("service_name", sa.String(length=100), nullable=False),
                sa.Column("instance_id", sa.String(length=255), nullable=False),
                sa.Column("status", sa.String(length=32), nullable=False),
                sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column(
                    "last_heartbeat_at", sa.DateTime(timezone=True), nullable=False
                ),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
                sa.PrimaryKeyConstraint("service_name"),
            ],
            "expected schema",
        ),
    ],
)
def test_worker_heartbeats_migration_upgrade_rejects_malformed_existing_table(
    table_columns,
    expected_error,
) -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("worker_heartbeats", metadata, *table_columns)
    metadata.create_all(engine)

    with engine.begin() as conn:
        worker_heartbeats_migration.op = _operations(conn)
        with pytest.raises(RuntimeError, match=expected_error):
            worker_heartbeats_migration.upgrade()
