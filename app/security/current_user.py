from __future__ import annotations

# Backwards-compatible re-exports to satisfy existing imports/tests.
from app.config import settings  # noqa: F401
from app.db import async_session_maker  # noqa: F401
from app.security import auth0  # noqa: F401
from app.security.dependencies import _env_name, get_current_user  # noqa: F401
