from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api import middleware_http
from app.api.app_builder import create_app
from app.api.middleware_http import configure_cors, configure_csrf_protection
from app.core.settings import settings


def _configure_security_settings(
    monkeypatch,
    *,
    env: str = "test",
    csrf_allowed_origins: list[str] | None = None,
    csrf_path_prefixes: list[str] | None = None,
    cors_allowed_origins: list[str] | None = None,
    cors_origin_regex: str | None = None,
) -> None:
    monkeypatch.setattr(settings, "ENV", env)
    monkeypatch.setattr(
        settings,
        "CSRF_ALLOWED_ORIGINS",
        csrf_allowed_origins or ["https://frontend.tenon.ai"],
    )
    monkeypatch.setattr(
        settings,
        "CSRF_PROTECTED_PATH_PREFIXES",
        csrf_path_prefixes or [],
    )
    monkeypatch.setattr(
        settings.cors,
        "CORS_ALLOW_ORIGINS",
        cors_allowed_origins or ["https://frontend.tenon.ai"],
    )
    monkeypatch.setattr(settings.cors, "CORS_ALLOW_ORIGIN_REGEX", cors_origin_regex)


def _csrf_app() -> FastAPI:
    app = FastAPI()

    @app.api_route(
        "/api/demo",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def demo():
        return {"ok": True}

    configure_csrf_protection(app)
    configure_cors(app)
    return app


@pytest.mark.asyncio
async def test_default_protected_prefix_covers_real_backend_route(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = create_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/auth/logout",
            headers={
                "Origin": "https://evil.example",
                "Cookie": "session=abc",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }


@pytest.mark.asyncio
async def test_protected_post_with_allowed_origin_succeeds(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={
                "Origin": "https://frontend.tenon.ai",
                "Cookie": "session=abc",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_protected_post_with_disallowed_origin_returns_csrf_error(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={"Origin": "https://evil.example", "Cookie": "session=abc"},
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }


@pytest.mark.asyncio
async def test_protected_post_without_origin_allows_matching_referer(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={
                "Referer": "https://frontend.tenon.ai/dashboard",
                "Cookie": "session=abc",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {"Cookie": "session=abc"},
        {"Referer": "https://evil.example/path", "Cookie": "session=abc"},
    ],
)
async def test_protected_post_without_origin_bad_or_missing_referer_rejected(
    monkeypatch, headers
):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post("/api/demo", headers=headers)

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }


@pytest.mark.asyncio
async def test_protected_post_with_malformed_referer_rejected(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={"Referer": "::::", "Cookie": "session=abc"},
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }


@pytest.mark.asyncio
async def test_safe_methods_are_not_csrf_blocked(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get(
            "/api/demo",
            headers={"Origin": "https://evil.example", "Cookie": "session=abc"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_preflight_allowed_origin_succeeds(monkeypatch):
    _configure_security_settings(monkeypatch, env="prod")
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.options(
            "/api/demo",
            headers={
                "Origin": "https://frontend.tenon.ai",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"] == "https://frontend.tenon.ai"
    )


@pytest.mark.asyncio
async def test_preflight_disallowed_origin_fails_in_non_local_env(monkeypatch):
    _configure_security_settings(monkeypatch, env="prod")
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.options(
            "/api/demo",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_protected_post_with_cookie_and_bearer_disallowed_origin_returns_csrf_error(
    monkeypatch,
):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={
                "Authorization": "Bearer integration-test-token",
                "Cookie": "session=abc",
                "Origin": "https://evil.example",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }


@pytest.mark.asyncio
async def test_bearer_only_requests_bypass_cookie_csrf_enforcement(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={
                "Authorization": "Bearer integration-test-token",
                "Origin": "https://evil.example",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_protected_prefix_mismatch_bypasses_csrf(monkeypatch):
    _configure_security_settings(
        monkeypatch, csrf_path_prefixes=["/api/protected-only"]
    )
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={"Origin": "https://evil.example", "Cookie": "session=abc"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_csrf_rejection_logs_exclude_cookie_and_authorization(
    monkeypatch, caplog: pytest.LogCaptureFixture
):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()
    caplog.set_level(logging.WARNING, logger="app.api.middleware_http")

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={
                "Origin": "https://evil.example",
                "Cookie": "session=abc",
                "Authorization": "Bearer integration-test-token",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }
    assert "session=abc" not in caplog.text
    assert "integration-test-token" not in caplog.text

    record = next(
        record for record in caplog.records if record.message == "csrf_origin_mismatch"
    )
    assert not hasattr(record, "cookie")
    assert not hasattr(record, "authorization")


def test_csrf_helpers_cover_edge_cases(monkeypatch):
    assert middleware_http._coerce_string_list(object()) == []
    assert middleware_http._coerce_string_list(" https://frontend.tenon.ai ") == [
        "https://frontend.tenon.ai"
    ]
    assert middleware_http._normalize_path_prefix("api/backend/") == "/api/backend"
    assert middleware_http._path_matches_prefixes("/anything", ["/"]) is True
    assert middleware_http._is_cookie_authenticated_request({}) is False
    assert (
        middleware_http._is_cookie_authenticated_request(
            {
                "cookie": "session=abc",
                "authorization": "Bearer integration-test-token",
            }
        )
        is True
    )

    monkeypatch.setattr(settings, "API_PREFIX", "/api")
    monkeypatch.setattr(settings, "CSRF_PROTECTED_PATH_PREFIXES", [])
    assert middleware_http._default_csrf_path_prefixes() == ["/api"]
    assert middleware_http._csrf_protected_prefixes() == ["/api"]

    monkeypatch.setattr(settings, "API_PREFIX", None)
    assert middleware_http._default_csrf_path_prefixes() == ["/api"]

    monkeypatch.setattr(settings, "API_PREFIX", "")
    assert middleware_http._default_csrf_path_prefixes() == ["/"]

    monkeypatch.setattr(settings, "ENV", "test")
    monkeypatch.setattr(settings, "CSRF_ALLOWED_ORIGINS", [])
    monkeypatch.setattr(settings.cors, "CORS_ALLOW_ORIGINS", [])
    monkeypatch.setattr(settings.cors, "CORS_ALLOW_ORIGIN_REGEX", None)
    assert set(middleware_http._csrf_allowed_origins()) == {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }

    # Exercise local/test fallback when CORS regex is set but CORS origin list is empty.
    monkeypatch.setattr(settings.cors, "CORS_ALLOW_ORIGIN_REGEX", r"^https://allowed")
    assert set(middleware_http._csrf_allowed_origins()) == {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }

    monkeypatch.setattr(settings, "ENV", "prod")
    assert middleware_http._csrf_allowed_origins() == []


def test_normalize_origin_rejects_malformed_values():
    assert middleware_http._normalize_origin(None) is None
    assert middleware_http._normalize_origin("http://[::1") is None
    assert middleware_http._normalize_origin("https://user@example.com") is None
    assert middleware_http._normalize_origin("https://example.com:abc") is None


@pytest.mark.asyncio
async def test_csrf_middleware_passes_non_http_scopes():
    called = {"value": False}

    async def app(scope, receive, send):
        called["value"] = True

    middleware = middleware_http.CsrfOriginEnforcementMiddleware(
        app,
        allowed_origins=["https://frontend.tenon.ai"],
        protected_path_prefixes=["/api"],
    )
    await middleware({"type": "lifespan"}, lambda: None, lambda _message: None)

    assert called["value"] is True
