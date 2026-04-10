from __future__ import annotations

import pytest

from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_test_utils import *


@pytest.mark.asyncio
async def test_find_marker_commit_sha_skips_non_match_and_blank_sha():
    marker = "winoe-marker"
    client = _BranchFailureGithub(
        commits=[
            {"sha": "", "commit": {"message": f"contains {marker} but blank sha"}},
            {"sha": "non-marker-sha", "commit": {"message": "no match here"}},
        ]
    )

    resolved = await precommit_service._find_marker_commit_sha(
        client,
        repo_full_name="org/workspace-repo",
        branch="main",
        marker=marker,
    )
    assert resolved is None
