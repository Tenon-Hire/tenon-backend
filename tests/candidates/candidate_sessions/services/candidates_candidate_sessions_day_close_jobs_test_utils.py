from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.candidates.candidate_sessions.services import day_close_jobs
from tests.shared.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)

__all__ = [
    "UTC",
    "SimpleNamespace",
    "create_candidate_session",
    "create_recruiter",
    "create_simulation",
    "datetime",
    "day_close_jobs",
    "timedelta",
]
