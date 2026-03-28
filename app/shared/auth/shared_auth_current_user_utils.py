from __future__ import annotations

# Backwards-compatible re-exports to satisfy existing imports/tests.
from app.config import settings  # noqa: F401
from app.shared.auth import auth0  # noqa: F401
from app.shared.auth.dependencies import (  # noqa: F401
    _env_name,
    get_authenticated_user,
    get_current_user,
)
from app.shared.database import async_session_maker  # noqa: F401
