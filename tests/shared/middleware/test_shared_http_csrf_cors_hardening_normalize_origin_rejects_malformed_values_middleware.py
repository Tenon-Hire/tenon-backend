from __future__ import annotations

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


def test_normalize_origin_rejects_malformed_values():
    assert middleware_http._normalize_origin(None) is None
    assert middleware_http._normalize_origin("http://[::1") is None
    assert middleware_http._normalize_origin("https://user@example.com") is None
    assert middleware_http._normalize_origin("https://example.com:abc") is None
