from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_middleware_http_configure_cors_defaults(monkeypatch):
    monkeypatch.setattr(middleware_http.settings, "cors", None)
    seen = {}

    class StubApp:
        def add_middleware(self, _mw, **kwargs):
            seen.update(kwargs)

    middleware_http.configure_cors(StubApp())
    assert "http://localhost:3000" in seen["allow_origins"]
