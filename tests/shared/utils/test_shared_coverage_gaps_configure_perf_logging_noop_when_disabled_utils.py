from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_configure_perf_logging_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(middleware_perf, "perf_logging_enabled", lambda: False)

    class StubApp:
        called = False

        def add_middleware(self, _mw):
            self.called = True

    app = StubApp()
    middleware_perf.configure_perf_logging(app)
    assert app.called is False
