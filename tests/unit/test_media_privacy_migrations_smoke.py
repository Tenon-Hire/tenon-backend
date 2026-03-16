from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    text,
)

_PRE_PRIVACY_REVISION = "202603150001"
_PRIVACY_REVISION = "202603150002"


def _build_pre_revision_schema(sqlite_url: str) -> None:
    engine = create_engine(sqlite_url)
    metadata = MetaData()

    Table(
        "candidate_sessions",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("simulation_id", Integer, nullable=False),
        Column("scenario_version_id", Integer, nullable=False),
        Column("candidate_name", String(255), nullable=False),
        Column("invite_email", String(255), nullable=False),
        Column("token", String(255), nullable=False),
        Column("status", String(50), nullable=False),
    )

    Table(
        "recording_assets",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("candidate_session_id", Integer, nullable=False),
        Column("task_id", Integer, nullable=False),
        Column("storage_key", String(1024), nullable=False),
        Column("content_type", String(255), nullable=False),
        Column("bytes", Integer, nullable=False),
        Column("status", String(50), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        CheckConstraint(
            "status IN ('uploading','uploaded','processing','ready','failed')",
            name="ck_recording_assets_status",
        ),
    )

    Table(
        "transcripts",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("recording_id", Integer, nullable=False),
        Column("status", String(50), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )

    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": _PRE_PRIVACY_REVISION},
        )


def _columns_for(sqlite_url: str, table_name: str) -> set[str]:
    engine = create_engine(sqlite_url)
    with engine.connect() as conn:
        return {col["name"] for col in inspect(conn).get_columns(table_name)}


def _run_alembic(repo_root: Path, *, sqlite_url: str, args: list[str]) -> None:
    env = os.environ.copy()
    env["TENON_ENV"] = "test"
    env["TENON_DATABASE_URL_SYNC"] = sqlite_url
    env["TENON_DATABASE_URL"] = sqlite_url
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


def test_media_privacy_migration_upgrade_and_downgrade_smoke(tmp_path):
    sqlite_path = tmp_path / "media_privacy_migration_smoke.db"
    sqlite_url = f"sqlite:///{sqlite_path}"
    _build_pre_revision_schema(sqlite_url)

    repo_root = Path(__file__).resolve().parents[2]

    _run_alembic(
        repo_root,
        sqlite_url=sqlite_url,
        args=["upgrade", _PRIVACY_REVISION],
    )

    candidate_session_columns = _columns_for(sqlite_url, "candidate_sessions")
    recording_columns = _columns_for(sqlite_url, "recording_assets")
    transcript_columns = _columns_for(sqlite_url, "transcripts")

    assert {"consent_version", "consent_timestamp", "ai_notice_version"}.issubset(
        candidate_session_columns
    )
    assert {
        "deleted_at",
        "purged_at",
        "consent_version",
        "consent_timestamp",
        "ai_notice_version",
    }.issubset(recording_columns)
    assert {"deleted_at"}.issubset(transcript_columns)

    _run_alembic(
        repo_root,
        sqlite_url=sqlite_url,
        args=["downgrade", _PRE_PRIVACY_REVISION],
    )

    downgraded_candidate_session_columns = _columns_for(
        sqlite_url, "candidate_sessions"
    )
    downgraded_recording_columns = _columns_for(sqlite_url, "recording_assets")
    downgraded_transcript_columns = _columns_for(sqlite_url, "transcripts")

    assert "consent_version" not in downgraded_candidate_session_columns
    assert "deleted_at" not in downgraded_recording_columns
    assert "purged_at" not in downgraded_recording_columns
    assert "deleted_at" not in downgraded_transcript_columns
