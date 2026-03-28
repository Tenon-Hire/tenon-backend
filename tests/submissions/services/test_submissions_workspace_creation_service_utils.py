from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.integrations.github import GithubError
from app.submissions.constants import WorkspaceMissing
from app.submissions.services import workspace_creation as wc


class _RollbackDB:
    def __init__(self) -> None:
        self.rollback_calls = 0

    async def rollback(self) -> None:
        self.rollback_calls += 1


@pytest.fixture(autouse=True)
def _stub_precommit_bundle_apply(monkeypatch):
    async def _no_bundle(*_args, **_kwargs):
        return SimpleNamespace(state="no_bundle", precommit_sha=None, bundle_id=None)

    monkeypatch.setattr(wc, "apply_precommit_bundle_if_available", _no_bundle)


__all__ = [name for name in globals() if not name.startswith("__")]
