from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core import db


@pytest.mark.asyncio
async def test_init_db_if_needed_is_noop(monkeypatch):
    called = False

    async def fake_begin():
        nonlocal called
        called = True
        yield None

    monkeypatch.setattr(db, "engine", SimpleNamespace(begin=fake_begin))
    await db.init_db_if_needed()
    assert called is False
