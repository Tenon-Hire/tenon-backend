from __future__ import annotations

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
def _workspace_creation_imports_are_current():
    assert hasattr(wc, "provision_workspace")


__all__ = [name for name in globals() if not name.startswith("__")]
