from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_ensure_canonical_workspace_url_updates_noncanonical_url():
    db = _DummyDB()
    workspace = SimpleNamespace(
        repo_full_name="acme/repo",
        codespace_url="https://example.com/old",
    )

    resolved = await codespace_urls.ensure_canonical_workspace_url(db, workspace)

    assert resolved.startswith("https://codespaces.new/acme/repo")
    assert workspace.codespace_url == resolved
    assert db.commits == 1
    assert db.refreshes == 1
