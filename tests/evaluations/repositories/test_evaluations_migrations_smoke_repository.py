from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

_PRE_EVALUATION_REVISION = "202603110001"
_EVALUATION_REVISION = "202603120002"


def _build_pre_revision_schema(sqlite_url: str) -> None:
    engine = create_engine(sqlite_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE candidate_sessions (id INTEGER PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE scenario_versions (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": _PRE_EVALUATION_REVISION},
        )


def _columns_for(sqlite_url: str, table_name: str) -> set[str]:
    engine = create_engine(sqlite_url)
    with engine.connect() as conn:
        return {col["name"] for col in inspect(conn).get_columns(table_name)}


def _table_names(sqlite_url: str) -> set[str]:
    engine = create_engine(sqlite_url)
    with engine.connect() as conn:
        return set(inspect(conn).get_table_names())


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


def test_evaluation_migration_upgrade_and_downgrade_smoke(tmp_path):
    sqlite_path = tmp_path / "evaluation_migration_smoke.db"
    sqlite_url = f"sqlite:///{sqlite_path}"
    _build_pre_revision_schema(sqlite_url)

    repo_root = Path(__file__).resolve().parents[3]

    _run_alembic(
        repo_root,
        sqlite_url=sqlite_url,
        args=["upgrade", _EVALUATION_REVISION],
    )
    run_columns = _columns_for(sqlite_url, "evaluation_runs")
    run_indexes = _indexes_for(sqlite_url, "evaluation_runs")
    day_score_columns = _columns_for(sqlite_url, "evaluation_day_scores")

    assert "candidate_session_id" in run_columns
    assert "scenario_version_id" in run_columns
    assert "day2_checkpoint_sha" in run_columns
    assert "day3_final_sha" in run_columns
    assert "cutoff_commit_sha" in run_columns
    assert "transcript_reference" in run_columns
    assert "job_id" in run_columns
    assert "basis_fingerprint" in run_columns
    assert "overall_fit_score" in run_columns
    assert "recommendation" in run_columns
    assert "confidence" in run_columns
    assert "generated_at" in run_columns
    assert "raw_report_json" in run_columns
    assert "error_code" in run_columns
    assert "ix_evaluation_runs_job_id" in run_indexes
    assert run_indexes["ix_evaluation_runs_job_id"]["column_names"] == ["job_id"]
    assert bool(run_indexes["ix_evaluation_runs_job_id"]["unique"]) is True

    assert "run_id" in day_score_columns
    assert "day_index" in day_score_columns
    assert "rubric_results_json" in day_score_columns
    assert "evidence_pointers_json" in day_score_columns

    _run_alembic(
        repo_root,
        sqlite_url=sqlite_url,
        args=["downgrade", _PRE_EVALUATION_REVISION],
    )
    tables_after_downgrade = _table_names(sqlite_url)
    assert "evaluation_runs" not in tables_after_downgrade
    assert "evaluation_day_scores" not in tables_after_downgrade
