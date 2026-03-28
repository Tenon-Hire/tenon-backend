from __future__ import annotations

import pytest

from app.integrations.github.client.integrations_github_client_github_client_compat_client import (
    CompatOperations,
)


class _CompatOpsUnderTest(CompatOperations):
    def __init__(self) -> None:
        self.transport = object()


@pytest.mark.asyncio
async def test_post_json_delegates_to_request_with_expect_body_flag():
    client = _CompatOpsUnderTest()
    captured: dict[str, object] = {}

    async def _fake_request(
        method: str,
        path: str,
        *,
        params=None,
        json=None,
        expect_body: bool = True,
    ):
        captured["method"] = method
        captured["path"] = path
        captured["params"] = params
        captured["json"] = json
        captured["expect_body"] = expect_body
        return {"ok": True}

    client._request = _fake_request  # type: ignore[method-assign]

    result = await client._post_json(
        "/repos/acme/repo/git/commits",
        json={"message": "commit"},
        expect_body=False,
    )

    assert result == {"ok": True}
    assert captured == {
        "method": "POST",
        "path": "/repos/acme/repo/git/commits",
        "params": None,
        "json": {"message": "commit"},
        "expect_body": False,
    }
