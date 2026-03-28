"""Application module for integrations github client github client compat client workflows."""

from __future__ import annotations

from .integrations_github_client_github_client_names_utils import split_full_name
from .integrations_github_client_github_client_requests_client import (
    get_bytes,
    request_json,
)
from .integrations_github_client_github_client_transport_client import GithubTransport


class CompatOperations:
    """Represent compat operations data and behavior."""

    transport: GithubTransport

    def _split_full_name(self, full_name: str):
        return split_full_name(full_name)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params=None,
        json=None,
        expect_body: bool = True,
    ):
        return await request_json(
            self.transport,
            method,
            path,
            params=params,
            json=json,
            expect_body=expect_body,
        )

    async def _get_json(self, path: str, params=None):
        return await self._request("GET", path, params=params)

    async def _post_json(self, path: str, *, json: dict, expect_body: bool = True):
        return await self._request("POST", path, json=json, expect_body=expect_body)

    async def _put_json(self, path: str, *, json: dict | None = None):
        return await self._request("PUT", path, json=json)

    async def _get_bytes(self, path: str, params=None) -> bytes:
        return await get_bytes(self.transport, path, params=params)
