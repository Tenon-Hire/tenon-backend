import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.config import settings
from app.shared.auth import auth0, principal


def _credentials_and_request(headers: list[tuple[bytes, bytes]] | None = None):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok"), Request(
        {"type": "http", "headers": headers or []}
    )


async def _assert_get_principal_error(
    monkeypatch,
    *,
    auth_error: auth0.Auth0Error,
    expected_status: int,
    expected_detail: str,
    headers: list[tuple[bytes, bytes]] | None = None,
):
    def bad_decode(_token: str):
        raise auth_error

    monkeypatch.setattr(auth0, "decode_auth0_token", bad_decode)
    credentials, request = _credentials_and_request(headers)
    with pytest.raises(HTTPException) as excinfo:
        await principal.get_principal(credentials, request)
    assert excinfo.value.status_code == expected_status
    assert excinfo.value.detail == expected_detail


@pytest.mark.asyncio
async def test_get_principal_auth0_error_does_not_crash(monkeypatch):
    await _assert_get_principal_error(
        monkeypatch,
        auth_error=auth0.Auth0Error("Invalid token"),
        expected_status=401,
        expected_detail="Not authenticated",
        headers=[(b"x-request-id", b"req-1")],
    )


@pytest.mark.asyncio
async def test_get_principal_missing_credentials_returns_401():
    request = Request({"type": "http", "headers": []})

    with pytest.raises(HTTPException) as excinfo:
        await principal.get_principal(None, request)
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_get_principal_maps_jwks_failure(monkeypatch):
    await _assert_get_principal_error(
        monkeypatch,
        auth_error=auth0.Auth0Error("Auth provider unavailable", status_code=503),
        expected_status=503,
        expected_detail="Auth provider unavailable",
    )


@pytest.mark.asyncio
async def test_get_principal_maps_kid_not_found(monkeypatch):
    await _assert_get_principal_error(
        monkeypatch,
        auth_error=auth0.Auth0Error("Signing key not found"),
        expected_status=401,
        expected_detail="Not authenticated",
    )


@pytest.mark.asyncio
async def test_get_principal_blocks_dev_shorthand_outside_test(monkeypatch):
    monkeypatch.setenv("TENON_ENV", "prod")
    monkeypatch.setattr(settings, "ENV", "prod")
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="candidate:blocked@example.com"
    )
    request = Request({"type": "http", "headers": []})

    with pytest.raises(HTTPException) as excinfo:
        await principal.get_principal(credentials, request)
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Not authenticated"
