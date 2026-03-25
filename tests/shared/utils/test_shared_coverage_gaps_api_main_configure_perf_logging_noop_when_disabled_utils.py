from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_api_main_configure_perf_logging_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(api_main, "perf_logging_enabled", lambda: False)

    class StubApp:
        called = False

        def add_middleware(self, _mw):
            self.called = True

    app = StubApp()
    api_main._configure_perf_logging(app)
    assert app.called is False
