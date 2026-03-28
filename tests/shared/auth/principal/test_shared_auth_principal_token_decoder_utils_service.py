from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.shared.auth import auth0
from app.shared.auth.principal import (
    shared_auth_principal_token_decoder_utils as token_decoder,
)


def _credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")


def test_decode_credentials_returns_claims_on_success(monkeypatch):
    claims = {"sub": "auth0|123", "email": "ok@test.com"}
    monkeypatch.setattr(
        token_decoder.auth0, "decode_auth0_token", lambda _token: claims
    )

    resolved = token_decoder.decode_credentials(_credentials(), request_id="req-ok")
    assert resolved == claims


@pytest.mark.parametrize(
    ("detail", "status_code", "expected_reason", "expected_status", "expected_detail"),
    [
        (
            "Invalid token header malformed",
            401,
            "invalid_header",
            401,
            "Not authenticated",
        ),
        ("Token header missing kid", 401, "kid_missing", 401, "Not authenticated"),
        ("Invalid token algorithm", 401, "invalid_algorithm", 401, "Not authenticated"),
        ("Wrong issuer", 401, "wrong_issuer", 401, "Not authenticated"),
        (
            "auth0 unavailable",
            503,
            "jwks_fetch_failed",
            503,
            "Auth provider unavailable",
        ),
    ],
)
def test_decode_credentials_maps_error_reasons(
    monkeypatch,
    detail: str,
    status_code: int,
    expected_reason: str,
    expected_status: int,
    expected_detail: str,
):
    captured: dict[str, object] = {}

    def _raise_auth0_error(_token: str):
        raise auth0.Auth0Error(detail, status_code=status_code)

    def _capture_warning(_message: str, *, extra: dict[str, object]):
        captured.update(extra)

    monkeypatch.setattr(token_decoder.auth0, "decode_auth0_token", _raise_auth0_error)
    monkeypatch.setattr(token_decoder.logger, "warning", _capture_warning)

    with pytest.raises(HTTPException) as excinfo:
        token_decoder.decode_credentials(_credentials(), request_id="req-123")

    assert excinfo.value.status_code == expected_status
    assert excinfo.value.detail == expected_detail
    assert captured["request_id"] == "req-123"
    assert captured["reason"] == expected_reason
