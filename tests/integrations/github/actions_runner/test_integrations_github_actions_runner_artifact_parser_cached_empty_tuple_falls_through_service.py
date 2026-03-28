from __future__ import annotations

import io
import json
import zipfile

import pytest

from app.integrations.github.actions_runner import (
    integrations_github_actions_runner_github_actions_runner_artifact_parser_service as artifact_parser,
)
from app.integrations.github.actions_runner import (
    integrations_github_actions_runner_github_actions_runner_cache_service as cache_service,
)
from app.integrations.github.client import GithubClient


@pytest.mark.asyncio
async def test_artifact_parser_cached_empty_tuple_falls_through_to_download():
    class _Client(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")
            self.download_calls = 0

        async def download_artifact_zip(self, *_args, **_kwargs):
            self.download_calls += 1
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr(
                    "tenon-test-results.json",
                    json.dumps({"passed": 2, "failed": 0, "total": 2}),
                )
            return buf.getvalue()

    client = _Client()
    cache = cache_service.ActionsCache()
    cache.artifact_cache[("org/repo", 77, 123)] = (None, None)

    parsed, error = await artifact_parser.parse_first_artifact(
        client=client,
        cache=cache,
        repo_full_name="org/repo",
        run_id=77,
        artifacts=[{"id": 123}],
    )

    assert error is None
    assert parsed is not None
    assert parsed.total == 2
    assert client.download_calls == 1
    await client.aclose()
