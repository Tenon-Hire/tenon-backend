from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_sqlalchemy_hooks_after_execute_handles_missing_stats():
    class EventImpl:
        def __init__(self):
            self.handlers = {}

        def listens_for(self, _target, name):
            def _decorator(fn):
                self.handlers[name] = fn
                return fn

            return _decorator

    event_impl = EventImpl()
    engine = SimpleNamespace(sync_engine=object())
    perf_ctx = SimpleNamespace(get=lambda: None)
    perf_module = SimpleNamespace(
        perf_logging_enabled=lambda: True,
        perf_sql_fingerprints_enabled=lambda: False,
    )
    sqlalchemy_hooks.register_listeners(
        engine,
        event_impl=event_impl,
        perf_ctx=perf_ctx,
        perf_module=perf_module,
    )
    context = SimpleNamespace()
    event_impl.handlers["before_cursor_execute"](None, None, None, None, context, False)
    event_impl.handlers["after_cursor_execute"](None, None, None, None, context, False)
