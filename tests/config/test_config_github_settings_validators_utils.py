from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import GithubSettings


def test_github_settings_reject_negative_workspace_retention_days():
    with pytest.raises(ValidationError):
        GithubSettings(WORKSPACE_RETENTION_DAYS=-1)


def test_github_settings_reject_invalid_cleanup_mode():
    with pytest.raises(ValidationError):
        GithubSettings(WORKSPACE_CLEANUP_MODE="purge")
