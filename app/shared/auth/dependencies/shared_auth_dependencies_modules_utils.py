"""Application module for auth dependencies modules utils workflows."""

from __future__ import annotations

import sys


def current_user_module():
    """Return the loaded current_user module."""
    return sys.modules.get("app.shared.auth.shared_auth_current_user_utils")
