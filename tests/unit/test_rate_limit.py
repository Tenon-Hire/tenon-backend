import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.infra.config import settings
from app.infra.security import rate_limit


def _request(host: str, headers: dict[str, str] | None = None):
    return SimpleNamespace(
        headers=headers or {},
        client=SimpleNamespace(host=host),
    )


def test_client_id_ignores_xff_when_untrusted(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", [])
    req = _request("10.1.2.3", {"x-forwarded-for": "203.0.113.5"})
    assert rate_limit.client_id(req) == "10.1.2.3"


def test_client_id_uses_xff_when_trusted(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", ["10.0.0.0/8"])
    req = _request("10.1.2.3", {"x-forwarded-for": "203.0.113.5"})
    assert rate_limit.client_id(req) == "203.0.113.5"


def test_throttle_includes_retry_after_header():
    limiter = rate_limit.RateLimiter()
    limiter.throttle("key", 10.0)
    with pytest.raises(HTTPException) as excinfo:
        limiter.throttle("key", 10.0)
    assert excinfo.value.headers["Retry-After"].isdigit()


@pytest.mark.asyncio
async def test_concurrency_guard_limits_in_flight():
    limiter = rate_limit.RateLimiter()
    entered = asyncio.Event()

    async def _hold():
        async with limiter.concurrency_guard("key", 1):
            entered.set()
            await asyncio.sleep(0.01)

    task = asyncio.create_task(_hold())
    await entered.wait()
    with pytest.raises(HTTPException):
        async with limiter.concurrency_guard("key", 1):
            pass
    await task
