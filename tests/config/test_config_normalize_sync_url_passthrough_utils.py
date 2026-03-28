from __future__ import annotations

from tests.config.config_test_utils import *


def test_normalize_sync_url_passthrough():
    from app.config import _normalize_sync_url

    assert _normalize_sync_url("sqlite:///local.db") == "sqlite:///local.db"
