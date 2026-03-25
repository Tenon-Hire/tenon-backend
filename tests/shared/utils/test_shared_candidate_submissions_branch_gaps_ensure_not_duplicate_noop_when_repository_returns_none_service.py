from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_ensure_not_duplicate_noop_when_repository_returns_none(monkeypatch):
    from app.submissions.services import (
        submissions_services_submissions_candidate_service as submission_service,
    )

    async def _no_duplicate(_db, _candidate_session_id, _task_id):
        return None

    monkeypatch.setattr(
        submission_service.submissions_repo,
        "find_duplicate",
        _no_duplicate,
    )

    await task_rules.ensure_not_duplicate(None, 10, 20)
