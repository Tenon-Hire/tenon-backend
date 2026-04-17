# ruff: noqa: E402
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("WINOE_ENV", "test")
os.environ.setdefault("WINOE_ADMIN_API_KEY", "test-admin-key")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

pytest_plugins = [
    "tests.shared.fixtures.shared_fixtures_core_utils",
    "tests.shared.fixtures.shared_fixtures_session_patch_utils",
    "tests.shared.fixtures.shared_fixtures_client_utils",
    "tests.shared.fixtures.shared_fixtures_actions_utils",
    "tests.shared.fixtures.shared_fixtures_header_utils",
]
