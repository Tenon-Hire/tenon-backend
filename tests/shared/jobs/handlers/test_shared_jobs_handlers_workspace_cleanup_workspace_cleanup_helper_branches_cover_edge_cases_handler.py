from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_helper_branches_cover_edge_cases():
    assert cleanup_handler._parse_positive_int(True) is None
    assert cleanup_handler._parse_positive_int("9") == 9
    assert cleanup_handler._parse_positive_int("abc") is None

    aware = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    assert cleanup_handler._normalize_datetime(aware) == aware

    assert (
        cleanup_handler._workspace_error_code(GithubError("err", status_code=None))
        == "github_request_failed"
    )
    assert cleanup_handler._workspace_error_code(RuntimeError("boom")) == "RuntimeError"
    assert (
        cleanup_handler._is_transient_github_error(
            GithubError("unknown transport", status_code=None)
        )
        is True
    )
    assert cleanup_handler._cleanup_target_repo_key(
        candidate_session_id=1,
        repo_full_name=None,
        fallback_id="fallback",
    ) == (1, "id:fallback")
