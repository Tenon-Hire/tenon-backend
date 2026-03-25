from __future__ import annotations

import pytest

from app.integrations.github.actions_runner import ActionsRunResult
from app.main import app
from app.shared.http.routes import tasks_codespaces as candidate_submissions
from tests.shared.fixtures.shared_fixtures_github_stub_client import StubGithubClient


@pytest.fixture
def actions_stubber():
    def _apply(result: ActionsRunResult | None = None, error: Exception | None = None):
        class StubActionsRunner:
            def __init__(self, res: ActionsRunResult | None, err: Exception | None):
                self._result = res or ActionsRunResult(
                    status="passed",
                    run_id=123,
                    conclusion="success",
                    passed=1,
                    failed=0,
                    total=1,
                    stdout="ok",
                    stderr=None,
                    head_sha="abc123",
                    html_url="https://example.com/run/123",
                    raw=None,
                )
                self._error = err

            async def dispatch_and_wait(self, **_kwargs):
                if self._error:
                    raise self._error
                return self._result

            async def fetch_run_result(self, **_kwargs):
                if self._error:
                    raise self._error
                return self._result

        runner = StubActionsRunner(result, error)
        app.dependency_overrides[candidate_submissions.get_actions_runner] = (
            lambda: runner
        )
        app.dependency_overrides[candidate_submissions.get_github_client] = (
            lambda: StubGithubClient()
        )
        return runner

    yield _apply
    app.dependency_overrides.pop(candidate_submissions.get_actions_runner, None)
    app.dependency_overrides.pop(candidate_submissions.get_github_client, None)
