from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_compat_operations_put_json_and_get_bytes(monkeypatch):
    class Ops(compat.CompatOperations):
        def __init__(self):
            self.transport = object()

    calls = {"request": [], "bytes": []}

    async def _request_json(_transport, method, path, **kwargs):
        calls["request"].append((method, path, kwargs))
        return {"ok": True}

    async def _get_bytes(_transport, path, params=None):
        calls["bytes"].append((path, params))
        return b"content"

    monkeypatch.setattr(compat, "request_json", _request_json)
    monkeypatch.setattr(compat, "get_bytes", _get_bytes)
    ops = Ops()
    await ops._put_json("/x", json={"a": 1})
    payload = await ops._get_bytes("/y", params={"q": "1"})
    assert calls["request"][0][0] == "PUT"
    assert calls["bytes"][0][0] == "/y"
    assert payload == b"content"
