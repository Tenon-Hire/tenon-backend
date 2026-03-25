from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_ensure_canonical_workspace_url_noop_when_equal_but_not_marked_canonical(
    monkeypatch,
):
    db = _DummyDB()
    canonical = "https://codespaces.new/acme/repo?quickstart=1"
    workspace = SimpleNamespace(
        repo_full_name="acme/repo",
        codespace_url=canonical,
    )

    monkeypatch.setattr(
        codespace_urls, "is_canonical_codespace_url", lambda _url: False
    )

    resolved = await codespace_urls.ensure_canonical_workspace_url(db, workspace)

    assert resolved == canonical
    assert workspace.codespace_url == canonical
    assert db.commits == 0
    assert db.refreshes == 0
