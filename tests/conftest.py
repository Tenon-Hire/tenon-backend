# ruff: noqa: E402
from __future__ import annotations

import os

os.environ.setdefault("WINOE_ENV", "test")
os.environ.setdefault("WINOE_ADMIN_API_KEY", "test-admin-key")

pytest_plugins = [
    "tests.shared.fixtures.shared_fixtures_core_utils",
    "tests.shared.fixtures.shared_fixtures_session_patch_utils",
    "tests.shared.fixtures.shared_fixtures_client_utils",
    "tests.shared.fixtures.shared_fixtures_actions_utils",
    "tests.shared.fixtures.shared_fixtures_header_utils",
]
