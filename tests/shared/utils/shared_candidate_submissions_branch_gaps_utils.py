from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_claims_service as claims_service,
)
from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_fetch_owned_service as fetch_owned_service,
)
from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_invites_service as invites_service,
)
from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_ownership_service as ownership_service,
)
from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_status_service as status_service,
)
from app.submissions.services import (
    submissions_services_submissions_codespace_urls_service as codespace_urls,
)
from app.submissions.services import (
    submissions_services_submissions_rate_limits_constants as rate_limits,
)
from app.submissions.services import (
    submissions_services_submissions_submission_progress_service as submission_progress,
)
from app.submissions.services import (
    submissions_services_submissions_task_rules_service as task_rules,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_codespace_init_service as codespace_init_service,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_submit_task_service as submit_task_service,
)


class _DummyDB:
    def __init__(self):
        self.commits = 0
        self.refreshes = 0
        self.flushes = 0

    async def commit(self):
        self.commits += 1

    async def refresh(self, _obj):
        self.refreshes += 1

    async def flush(self):
        self.flushes += 1

    @asynccontextmanager
    async def begin_nested(self):
        yield


__all__ = [name for name in globals() if not name.startswith("__")]
