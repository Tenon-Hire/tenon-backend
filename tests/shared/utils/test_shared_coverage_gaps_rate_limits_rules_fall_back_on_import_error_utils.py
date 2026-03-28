from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_rate_limits_rules_fall_back_on_import_error(monkeypatch):
    original_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.shared.http.routes" and "tasks_codespaces" in fromlist:
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)
    assert rate_limits._rules() == rate_limits._DEFAULT_RATE_LIMIT_RULES
