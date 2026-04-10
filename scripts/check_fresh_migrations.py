#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url


def _normalize_sync_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _resolve_sync_url(project_root: Path) -> str:
    env_url = os.getenv("WINOE_DATABASE_URL_SYNC") or os.getenv("WINOE_DATABASE_URL")
    if env_url:
        normalized = _normalize_sync_url(env_url)
    else:
        env_file = dotenv_values(project_root / ".env")
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
            "Fresh migration check requires a PostgreSQL sync URL. "
            f"Got: {normalized}"
        )
    return normalized


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    base_sync_url = _resolve_sync_url(project_root)
    base_url = make_url(base_sync_url)
    admin_url = base_url.set(database="postgres").render_as_string(hide_password=False)
    temp_db_name = f"winoe_migration_smoke_{uuid.uuid4().hex[:12]}"
    temp_sync_url = base_url.set(database=temp_db_name).render_as_string(
        hide_password=False
    )

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{temp_db_name}"'))

        env = os.environ.copy()
        env["WINOE_ENV"] = "test"
        env["WINOE_DATABASE_URL_SYNC"] = temp_sync_url
        env["WINOE_DATABASE_URL"] = temp_sync_url
        subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(project_root / "alembic.ini"),
                "upgrade",
                "heads",
            ],
            cwd=project_root,
            env=env,
            check=True,
        )
    finally:
        try:
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


if __name__ == "__main__":
    main()
