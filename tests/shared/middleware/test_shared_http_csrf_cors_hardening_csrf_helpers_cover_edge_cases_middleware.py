from __future__ import annotations

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


def test_csrf_helpers_cover_edge_cases(monkeypatch):
    assert middleware_http._coerce_string_list(object()) == []
    assert middleware_http._coerce_string_list(" https://frontend.tenon.ai ") == [
        "https://frontend.tenon.ai"
    ]
    assert middleware_http._normalize_path_prefix("api/backend/") == "/api/backend"
    assert middleware_http._normalize_path_prefix("/") == "/"
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
    monkeypatch.setattr(
        settings,
        "CSRF_PROTECTED_PATH_PREFIXES",
        [" /api/ ", "/api", " ", ""],
    )
    assert middleware_http._csrf_protected_prefixes() == ["/api"]

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
