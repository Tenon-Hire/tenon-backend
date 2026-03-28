from __future__ import annotations

from tests.config.config_test_utils import *


def test_database_url_async_adds_asyncpg_driver():
    s = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/dbname",
        DATABASE_URL_SYNC="postgresql://user:pass@localhost:5432/dbname",
    )
    assert (
        s.database_url_async == "postgresql+asyncpg://user:pass@localhost:5432/dbname"
    )
