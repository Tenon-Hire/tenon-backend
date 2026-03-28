from __future__ import annotations

from tests.config.config_test_utils import *


def test_to_async_url_passthrough_and_coerce():
    assert _to_async_url("sqlite:///local.db") == "sqlite+aiosqlite:///local.db"
    assert (
        _to_async_url("postgresql://user:pass@localhost/db")
        == "postgresql+asyncpg://user:pass@localhost/db"
    )
