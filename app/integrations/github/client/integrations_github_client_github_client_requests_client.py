"""Application module for integrations github client github client requests client workflows."""

from __future__ import annotations

import logging
import time

import httpx

from app.shared.utils import shared_utils_perf_utils as perf

from .integrations_github_client_github_client_errors_client import (
    GithubError,
    raise_for_status,
)
from .integrations_github_client_github_client_transport_client import GithubTransport

logger = logging.getLogger(__name__)


async def request_json(
    transport: GithubTransport,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
    expect_body: bool = True,
) -> dict:
    """Execute request json."""
    started = time.perf_counter()
    try:
        resp = await transport.client().request(method, path, params=params, json=json)
    except httpx.HTTPError as exc:  # pragma: no cover - network
        logger.error(
            "github_request_failed",
            extra={"url": f"{transport.base_url}{path}", "error": str(exc)},
        )
        raise GithubError("GitHub request failed") from exc
    finally:
        perf.record_external_wait("github", (time.perf_counter() - started) * 1000.0)

    raise_for_status(str(resp.url), resp)
    if not expect_body:
        return {}
    if "application/zip" in resp.headers.get("Content-Type", ""):
        return resp.content  # type: ignore[return-value]
    try:
        return resp.json()
    except ValueError as exc:
        raise GithubError("Invalid GitHub response") from exc


async def get_bytes(
    transport: GithubTransport, path: str, params: dict | None = None
) -> bytes:
    """Return bytes."""
    started = time.perf_counter()
    try:
        resp = await transport.client().get(path, params=params, follow_redirects=True)
    except httpx.HTTPError as exc:  # pragma: no cover - network
        logger.error(
            "github_request_failed",
            extra={"url": f"{transport.base_url}{path}", "error": str(exc)},
        )
        raise GithubError("GitHub request failed") from exc
    finally:
        perf.record_external_wait("github", (time.perf_counter() - started) * 1000.0)

    raise_for_status(str(resp.url), resp)
    return resp.content
