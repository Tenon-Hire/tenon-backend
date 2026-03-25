from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_register_error_handlers_registers_both_types():
    seen = []

    class StubApp:
        def add_exception_handler(self, exc, handler):
            seen.append((exc, handler))

    error_utils.register_error_handlers(StubApp())
    assert len(seen) == 2
