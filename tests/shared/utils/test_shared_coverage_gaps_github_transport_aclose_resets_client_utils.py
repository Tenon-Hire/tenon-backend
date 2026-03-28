from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_github_transport_aclose_resets_client():
    gh_transport = transport.GithubTransport(
        base_url="https://api.github.com", token="t"
    )
    _ = gh_transport.client()
    assert gh_transport._client is not None
    await gh_transport.aclose()
    assert gh_transport._client is None
