from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.config import settings
from app.integrations.github.actions_runner import ActionsRunResult
from app.integrations.github.client import GithubError
from app.shared.auth.principal import Principal
from app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils import (
    candidate_session_from_headers,
)
from app.shared.http.routes import tasks_codespaces as candidate_submissions
from app.submissions.schemas.submissions_schemas_submissions_requests_schema import (
    CodespaceInitRequest,
    RunTestsRequest,
    SubmissionCreateRequest,
)


def _async_return(val):
    async def _inner(*_a, **_kw):
        return val

    return _inner


def _stub_cs():
    return SimpleNamespace(
        id=1,
        trial_id=1,
        status="in_progress",
        scheduled_start_at=datetime.now(UTC) - timedelta(days=1),
    )


def _stub_task():
    return SimpleNamespace(
        id=2,
        trial_id=1,
        type="code",
        template_repo="org/template",
        day_index=2,
        title="t",
        description="d",
    )


def _stub_workspace():
    return SimpleNamespace(
        repo_full_name="org/repo",
        default_branch="main",
        id="ws1",
        base_template_sha="base",
        precommit_sha=None,
        last_test_summary_json=None,
        latest_commit_sha=None,
        last_workflow_run_id=None,
        last_workflow_conclusion=None,
        last_test_summary=None,
        codespace_name=None,
        codespace_url=None,
        codespace_state=None,
    )


def _principal(email: str = "candidate@example.com") -> Principal:
    email_claim = settings.auth.AUTH0_EMAIL_CLAIM
    permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
    return Principal(
        sub=f"auth0|{email}",
        email=email,
        name=email.split("@")[0],
        roles=[],
        permissions=["candidate:access"],
        claims={
            "sub": f"auth0|{email}",
            "email": email,
            email_claim: email,
            "permissions": ["candidate:access"],
            permissions_claim: ["candidate:access"],
        },
    )


@pytest.fixture(autouse=True)
def _disable_task_window_guard(monkeypatch):
    monkeypatch.setattr(
        candidate_submissions.cs_service,
        "require_active_window",
        lambda *_a, **_k: None,
    )


__all__ = [name for name in globals() if not name.startswith("__")]
