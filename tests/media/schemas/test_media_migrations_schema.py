from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

_PRE_MEDIA_POINTER_REVISION = "202603100003"
_MEDIA_POINTER_REVISION = "202603110001"


def _build_pre_revision_schema(sqlite_url: str) -> None:
    engine = create_engine(sqlite_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE recording_assets (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                """
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY,
                    candidate_session_id INTEGER,
                    task_id INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE transcripts (
                    id INTEGER PRIMARY KEY,
                    recording_id INTEGER,
                    text TEXT,
                    segments_json JSON,
                    model_name VARCHAR(128),
                    status VARCHAR(32),
                    created_at DATETIME
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": _PRE_MEDIA_POINTER_REVISION},
        )


def _columns_for(sqlite_url: str, table_name: str) -> set[str]:
    engine = create_engine(sqlite_url)
    with engine.connect() as conn:
        return {col["name"] for col in inspect(conn).get_columns(table_name)}


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


def test_media_pointer_migration_upgrade_and_downgrade_smoke(tmp_path):
    sqlite_path = tmp_path / "media_pointer_migration_smoke.db"
    sqlite_url = f"sqlite:///{sqlite_path}"
    _build_pre_revision_schema(sqlite_url)

    repo_root = Path(__file__).resolve().parents[3]

    _run_alembic(
        repo_root,
        sqlite_url=sqlite_url,
        args=["upgrade", _MEDIA_POINTER_REVISION],
    )
    submission_columns = _columns_for(sqlite_url, "submissions")
    transcript_columns = _columns_for(sqlite_url, "transcripts")
    assert "recording_id" in submission_columns
    assert "last_error" in transcript_columns

    _run_alembic(
        repo_root,
        sqlite_url=sqlite_url,
        args=["downgrade", _PRE_MEDIA_POINTER_REVISION],
    )
    downgraded_submission_columns = _columns_for(sqlite_url, "submissions")
    downgraded_transcript_columns = _columns_for(sqlite_url, "transcripts")
    assert "recording_id" not in downgraded_submission_columns
    assert "last_error" not in downgraded_transcript_columns
