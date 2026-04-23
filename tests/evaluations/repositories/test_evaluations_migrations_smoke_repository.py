from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine.url import make_url


def _columns_for(sqlite_url: str, table_name: str) -> set[str]:
    engine = create_engine(sqlite_url)
    with engine.connect() as conn:
        return {col["name"] for col in inspect(conn).get_columns(table_name)}


def _table_names(sqlite_url: str) -> set[str]:
    engine = create_engine(sqlite_url)
    with engine.connect() as conn:
        return set(inspect(conn).get_table_names())


def _normalize_sync_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _resolve_sync_url(repo_root: Path) -> str:
    env_url = os.getenv("WINOE_DATABASE_URL_SYNC") or os.getenv("WINOE_DATABASE_URL")
    if env_url:
        normalized = _normalize_sync_url(env_url)
    else:
        env_file = dotenv_values(repo_root / ".env")
        file_url = env_file.get("WINOE_DATABASE_URL_SYNC") or env_file.get(
            "WINOE_DATABASE_URL"
        )
        if not file_url:
            raise RuntimeError(
                "WINOE_DATABASE_URL_SYNC or WINOE_DATABASE_URL must be set "
                "(env or .env)."
            )
        normalized = _normalize_sync_url(str(file_url))

    if not normalized.startswith("postgresql://"):
        raise RuntimeError(
            "Fresh migration smoke test requires a PostgreSQL sync URL. "
            f"Got: {normalized}"
        )
    return normalized


def _temp_postgres_url(base_sync_url: str) -> tuple[str, str]:
    base_url = make_url(base_sync_url)
    temp_db_name = f"winoe_migration_smoke_{uuid.uuid4().hex[:12]}"
    temp_sync_url = base_url.set(database=temp_db_name).render_as_string(
        hide_password=False
    )
    admin_url = base_url.set(database="postgres").render_as_string(hide_password=False)
    return admin_url, temp_sync_url


def _run_alembic_heads(repo_root: Path, *, sync_url: str) -> None:
    env = os.environ.copy()
    env["WINOE_ENV"] = "test"
    env["WINOE_DATABASE_URL_SYNC"] = sync_url
    env["WINOE_DATABASE_URL"] = sync_url
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(repo_root / "alembic.ini"),
            "upgrade",
            "heads",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Alembic command failed: upgrade heads\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_evaluation_migration_upgrade_head_smoke():
    repo_root = Path(__file__).resolve().parents[3]
    base_sync_url = _resolve_sync_url(repo_root)
    admin_url, temp_sync_url = _temp_postgres_url(base_sync_url)
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        temp_db_name = make_url(temp_sync_url).database
        assert temp_db_name is not None
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{temp_db_name}"'))

        _run_alembic_heads(repo_root, sync_url=temp_sync_url)

        engine = create_engine(temp_sync_url)
        with engine.connect() as conn:
            version_num = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert version_num is not None

        tables_after_upgrade = _table_names(temp_sync_url)
        assert "notification_delivery_audits" in tables_after_upgrade
        assert "evaluation_reviewer_reports" in tables_after_upgrade

        run_columns = _columns_for(temp_sync_url, "evaluation_runs")
        day_score_columns = _columns_for(temp_sync_url, "evaluation_day_scores")
        reviewer_report_columns = _columns_for(
            temp_sync_url, "evaluation_reviewer_reports"
        )

        assert "id" in run_columns
        assert "candidate_session_id" in run_columns
        assert "scenario_version_id" in run_columns

        assert "id" in day_score_columns
        assert "run_id" in day_score_columns
        assert "day_index" in day_score_columns
        assert "rubric_results_json" in day_score_columns
        assert "evidence_pointers_json" in day_score_columns

        assert "run_id" in reviewer_report_columns
        assert "reviewer_agent_key" in reviewer_report_columns
        assert "day_index" in reviewer_report_columns
        assert "submission_kind" in reviewer_report_columns
        assert "score" in reviewer_report_columns
        assert "dimensional_scores_json" in reviewer_report_columns
        assert "evidence_citations_json" in reviewer_report_columns
        assert "assessment_text" in reviewer_report_columns
        assert "strengths_json" in reviewer_report_columns
        assert "risks_json" in reviewer_report_columns
        assert "raw_output_json" in reviewer_report_columns
    finally:
        try:
            temp_db_name = make_url(temp_sync_url).database
            assert temp_db_name is not None
            with admin_engine.connect() as conn:
                conn.execute(
                    text(
                        """
                        SELECT pg_terminate_backend(pid)
                          FROM pg_stat_activity
                         WHERE datname = :db_name
                           AND pid <> pg_backend_pid()
                        """
                    ),
                    {"db_name": temp_db_name},
                )
                conn.execute(text(f'DROP DATABASE IF EXISTS "{temp_db_name}"'))
        finally:
            admin_engine.dispose()
