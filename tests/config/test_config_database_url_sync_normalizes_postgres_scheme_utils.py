from __future__ import annotations

from tests.config.config_test_utils import *


def test_database_url_sync_normalizes_postgres_scheme():
    s = Settings(
        DATABASE_URL_SYNC="postgres://user:pass@localhost:5432/db",
        DATABASE_URL="",
    )
    assert s.database_url_sync == "postgresql://user:pass@localhost:5432/db"
