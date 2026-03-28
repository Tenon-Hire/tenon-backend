from __future__ import annotations

import pytest

from tests.integrations.github.client.test_integrations_github_client_utils import *


def test_split_full_name_rejects_empty_owner_or_repo():
    client = _mock_client(lambda r: httpx.Response(200, json={}))
    with pytest.raises(GithubError):
        client._split_full_name("owner/")
