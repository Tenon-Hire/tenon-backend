from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_submissions_helpers_guard_falls_back_when_router_import_fails(monkeypatch):
    guard = importlib.import_module(
        "app.submissions.routes.submissions_routes_submissions_helpers_guard_routes"
    )
    calls = {"fallback": 0}
    monkeypatch.setattr(
        guard, "ensure_talent_partner", lambda _u: calls.__setitem__("fallback", 1)
    )
    original_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.shared.http.routes" and "submissions" in fromlist:
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)
    guard.ensure_talent_partner_guard(SimpleNamespace(id=1))
    assert calls["fallback"] == 1
