import pytest

from app import api
from app.infra import perf


@pytest.mark.asyncio
async def test_lifespan_swallows_shutdown_errors(monkeypatch):
    called = {"closed": False}

    def fake_singleton():
        class _C:
            async def aclose(self):
                called["closed"] = True
                raise RuntimeError("boom")

        return _C()

    from app.api import dependencies as deps  # local import to patch actual singleton

    monkeypatch.setattr(deps.github_native, "_github_client_singleton", fake_singleton)
    async with api.main.lifespan(api.main.app):
        pass
    assert called["closed"] is True


def test_cors_config_defaults(monkeypatch):
    monkeypatch.setattr(api.main.settings, "cors", None)
    origins, regex = api.main._cors_config()
    assert {"http://localhost:3000", "http://127.0.0.1:3000"} <= set(origins)
    assert regex is None


def test_configure_perf_logging_when_enabled(monkeypatch):
    monkeypatch.setattr(api.main, "perf_logging_enabled", lambda: True)

    class DummyEngine:
        sync_engine = object()

    calls = {}

    def fake_attach(engine):
        calls["engine"] = engine

    monkeypatch.setattr(api.main, "engine", DummyEngine(), raising=False)
    monkeypatch.setattr(api.main, "attach_sqlalchemy_listeners", fake_attach, raising=False)

    class DummyApp:
        def __init__(self):
            self.middlewares = []

        def add_middleware(self, mw):
            self.middlewares.append(mw)

    app_obj = DummyApp()
    api.main._configure_perf_logging(app_obj)
    assert calls["engine"] is api.main.engine
    assert perf.RequestPerfMiddleware in app_obj.middlewares
