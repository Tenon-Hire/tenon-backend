import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.config import settings
from app.shared.auth import auth0, principal
from app.shared.auth.principal import (
    shared_auth_principal_dependencies_utils as principal_dependencies,
)
from app.shared.auth.principal.shared_auth_principal_model import Principal


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


@pytest.mark.asyncio
async def test_get_principal_blank_token_returns_401():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="   ")
    request = Request({"type": "http", "headers": []})

    with pytest.raises(HTTPException) as excinfo:
        await principal.get_principal(credentials, request)
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_get_principal_non_bearer_scheme_returns_401():
    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="token")
    request = Request({"type": "http", "headers": []})

    with pytest.raises(HTTPException) as excinfo:
        await principal.get_principal(credentials, request)
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_get_principal_allows_local_dev_bypass_for_local_client(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "local")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="candidate:local-bypass@example.com"
    )
    request = Request(
        {
            "type": "http",
            "headers": [],
            "client": ("127.0.0.1", 9000),
        }
    )

    resolved = await principal.get_principal(credentials, request)
    assert resolved.sub == "candidate:local-bypass@example.com"
    assert resolved.email == "local-bypass@example.com"
    assert "candidate:access" in resolved.permissions


@pytest.mark.asyncio
async def test_get_principal_direct_dev_principal_fallback_short_circuits_decoder(
    monkeypatch,
):
    expected_principal = Principal(
        sub="auth0|test",
        email="fallback@example.com",
        name="fallback",
        roles=["candidate"],
        permissions=["candidate:access"],
        claims={"sub": "auth0|test", "email": "fallback@example.com"},
    )

    def _build_dev_principal(_credentials):
        return expected_principal

    def _decode_credentials(*_args, **_kwargs):
        raise AssertionError("decode_credentials should not be called")

    monkeypatch.setattr(
        principal_dependencies, "build_dev_principal", _build_dev_principal
    )
    monkeypatch.setattr(
        principal_dependencies, "decode_credentials", _decode_credentials
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="opaque-token"
    )
    request = Request({"type": "http", "headers": []})

    resolved = await principal.get_principal(credentials, request)
    assert resolved is expected_principal


@pytest.mark.asyncio
async def test_get_principal_dev_token_in_test_env_without_dev_principal_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(settings, "ENV", "test")
    monkeypatch.setattr(
        principal_dependencies, "build_dev_principal", lambda _cred: None
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="candidate:no-build@example.com"
    )
    request = Request({"type": "http", "headers": []})

    with pytest.raises(HTTPException) as excinfo:
        await principal.get_principal(credentials, request)
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_get_principal_reraises_non_401_build_principal_error(monkeypatch):
    monkeypatch.setattr(
        principal_dependencies, "build_dev_principal", lambda _cred: None
    )
    monkeypatch.setattr(
        principal_dependencies,
        "decode_credentials",
        lambda _credentials, _request_id: {"sub": "auth0|x", "email": "x@test.com"},
    )

    def _raise_non_auth_error(_claims):
        raise HTTPException(status_code=500, detail="claims exploded")

    monkeypatch.setattr(
        principal_dependencies, "build_principal", _raise_non_auth_error
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="opaque-token"
    )
    request = Request({"type": "http", "headers": [(b"x-request-id", b"req-500")]})

    with pytest.raises(HTTPException) as excinfo:
        await principal.get_principal(credentials, request)
    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "claims exploded"
