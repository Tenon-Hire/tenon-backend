from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

_PRE_WORKSPACE_GROUP_CLEANUP_REVISION = "202603130002"
_WORKSPACE_GROUP_CLEANUP_REVISION = "202603130003"


def _build_pre_revision_schema(sqlite_url: str) -> None:
    engine = create_engine(sqlite_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE workspace_groups (
                    id VARCHAR(36) PRIMARY KEY,
                    candidate_session_id INTEGER,
                    workspace_key VARCHAR(64),
                    template_repo_full_name VARCHAR(255),
                    repo_full_name VARCHAR(255),
                    default_branch VARCHAR(120),
                    base_template_sha VARCHAR(100),
                    created_at DATETIME
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": _PRE_WORKSPACE_GROUP_CLEANUP_REVISION},
        )


def _columns_for(sqlite_url: str, table_name: str) -> set[str]:
    engine = create_engine(sqlite_url)
    with engine.connect() as conn:
        return {col["name"] for col in inspect(conn).get_columns(table_name)}


def _indexes_for(sqlite_url: str, table_name: str) -> dict[str, dict]:
    engine = create_engine(sqlite_url)
    with engine.connect() as conn:
        return {index["name"]: index for index in inspect(conn).get_indexes(table_name)}


def _run_alembic(repo_root: Path, *, sqlite_url: str, args: list[str]) -> None:
    env = os.environ.copy()
    env["WINOE_ENV"] = "test"
    env["WINOE_DATABASE_URL_SYNC"] = sqlite_url
    env["WINOE_DATABASE_URL"] = sqlite_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(repo_root / "alembic.ini"), *args],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Alembic command failed: {' '.join(args)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_workspace_group_cleanup_migration_upgrade_and_downgrade_smoke(tmp_path):
    sqlite_path = tmp_path / "workspace_group_cleanup_migration_smoke.db"
    sqlite_url = f"sqlite:///{sqlite_path}"
    _build_pre_revision_schema(sqlite_url)

    repo_root = Path(__file__).resolve().parents[3]

    _run_alembic(
        repo_root,
        sqlite_url=sqlite_url,
        args=["upgrade", _WORKSPACE_GROUP_CLEANUP_REVISION],
    )
    upgraded_columns = _columns_for(sqlite_url, "workspace_groups")
    upgraded_indexes = _indexes_for(sqlite_url, "workspace_groups")

    assert "cleanup_status" in upgraded_columns
    assert "cleanup_attempted_at" in upgraded_columns
    assert "cleaned_at" in upgraded_columns
    assert "cleanup_error" in upgraded_columns
    assert "retention_expires_at" in upgraded_columns
    assert "access_revoked_at" in upgraded_columns
    assert "access_revocation_error" in upgraded_columns
    assert "ix_workspace_groups_cleanup_status" in upgraded_indexes
    assert "ix_workspace_groups_retention_expires_at" in upgraded_indexes

    _run_alembic(
        repo_root,
        sqlite_url=sqlite_url,
        args=["downgrade", _PRE_WORKSPACE_GROUP_CLEANUP_REVISION],
    )
    downgraded_columns = _columns_for(sqlite_url, "workspace_groups")
    downgraded_indexes = _indexes_for(sqlite_url, "workspace_groups")

    assert "cleanup_status" not in downgraded_columns
    assert "cleanup_attempted_at" not in downgraded_columns
    assert "cleaned_at" not in downgraded_columns
    assert "cleanup_error" not in downgraded_columns
    assert "retention_expires_at" not in downgraded_columns
    assert "access_revoked_at" not in downgraded_columns
    assert "access_revocation_error" not in downgraded_columns
    assert "ix_workspace_groups_cleanup_status" not in downgraded_indexes
    assert "ix_workspace_groups_retention_expires_at" not in downgraded_indexes
