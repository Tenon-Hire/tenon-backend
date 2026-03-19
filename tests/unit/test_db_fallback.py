import pytest

from app.core import db


def test_create_engine_raises_when_database_url_missing(monkeypatch):
    class FakeSettings:
        @property
        def async_url(self):
            raise ValueError("missing")

    fake_settings = FakeSettings()
    monkeypatch.setattr(db, "settings", type("Obj", (), {"database": fake_settings}))
    with pytest.raises(ValueError, match="missing"):
        db._create_engine()
