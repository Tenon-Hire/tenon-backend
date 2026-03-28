from __future__ import annotations

from tests.config.config_test_utils import *


def test_normalize_sync_url_noop_and_getattr_passthrough():
    s = Settings(DATABASE_URL_SYNC="postgresql://already-normalized")
    assert s.database.sync_url == "postgresql://already-normalized"
    # Force __getattr__ path for AUTH0_JWKS_URL
    assert Settings.__getattr__(s, "AUTH0_JWKS_URL") == s.auth.AUTH0_JWKS_URL
