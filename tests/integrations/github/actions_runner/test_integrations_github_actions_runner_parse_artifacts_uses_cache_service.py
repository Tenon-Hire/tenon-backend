from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_parse_artifacts_uses_cache():
    class CacheClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")
            self.downloads = 0
            self.list_calls = 0

        async def list_artifacts(self, *_a, **_k):
            self.list_calls += 1
            return [{"id": 123, "name": "winoe-test-results"}]

        async def download_artifact_zip(self, *_a, **_k):
            self.downloads += 1
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr(
                    "winoe-test-results.json",
                    json.dumps({"passed": 1, "failed": 0, "total": 1}),
                )
            return buf.getvalue()

    client = CacheClient()
    runner = GithubActionsRunner(client, workflow_file="ci.yml")

    parsed_first, err_first = await runner._parse_artifacts("org/repo", 9)
    parsed_second, err_second = await runner._parse_artifacts("org/repo", 9)

    assert client.list_calls == 1
    assert client.downloads == 1
    assert err_first is None and err_second is None
    assert parsed_first and parsed_first.total == 1
    assert parsed_second and parsed_second.total == 1
    await client.aclose()
