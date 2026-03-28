"""Own the shared HTTP transport used by the GitHub API client layer."""

from __future__ import annotations

import httpx

from app.shared.utils.shared_utils_brand_utils import DEFAULT_USER_AGENT


class GithubTransport:
    """Lazily construct and close an ``httpx.AsyncClient`` with GitHub defaults."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._transport = transport
        self._headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        self._client: httpx.AsyncClient | None = None

    def client(self) -> httpx.AsyncClient:
        """Return a cached async client so callers reuse pooled connections."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers,
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
                transport=self._transport,
            )
        return self._client

    async def aclose(self) -> None:
        """Close and clear the cached async client if one has been created."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
