from __future__ import annotations

from app.core.auth import auth0  # noqa: F401
from app.core.auth.dependencies import (  # noqa: F401
    _env_name,
    get_authenticated_user,
    get_current_user,
)
from app.core.db import async_session_maker  # noqa: F401

# Backwards-compatible re-exports to satisfy existing imports/tests.
from app.core.settings import settings  # noqa: F401
