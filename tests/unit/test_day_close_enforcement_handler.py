from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.integrations.github import GithubError
from app.jobs import worker
from app.jobs.handlers import day_close_enforcement as enforcement_handler
from app.repositories.candidate_sessions import repository as cs_repo
from app.repositories.github_native.workspaces import repository as workspace_repo
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import JOB_STATUS_QUEUED, JOB_STATUS_SUCCEEDED
from app.services.candidate_sessions.day_close_jobs import (
    DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
    build_day_close_enforcement_payload,
    day_close_enforcement_idempotency_key,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


@pytest.fixture(autouse=True)
def _clear_job_handlers():
    worker.clear_handlers()
    yield
    worker.clear_handlers()


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )


async def _prepare_code_day_context(async_session: AsyncSession):
    recruiter = await create_recruiter(
        async_session, email="cutoff-enforcement-handler@test.com"
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    candidate_session.github_username = "octocat"
    day2_task = next(task for task in tasks if task.day_index == 2)
    now = datetime.now(UTC).replace(microsecond=0)

    group = await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/candidate-repo",
        default_branch="main",
        base_template_sha="template-base-sha",
        created_at=now,
    )
    await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=group.id,
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        template_repo_full_name=group.template_repo_full_name,
        repo_full_name=group.repo_full_name,
        repo_id=12345,
        default_branch=group.default_branch,
        base_template_sha=group.base_template_sha,
        created_at=now,
    )
    await async_session.commit()

    cutoff_at = now + timedelta(hours=1)
    payload = build_day_close_enforcement_payload(
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        day_index=day2_task.day_index,
        window_end_at=cutoff_at,
    )
    return simulation, candidate_session, day2_task, cutoff_at, payload


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_persists_cutoff_and_revokes_collaborator(
    async_session,
    monkeypatch,
):
    (
        _simulation,
        candidate_session,
        day2_task,
        cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)

    class StubGithubClient:
        def __init__(self):
            self.calls: list[tuple[str, str, str]] = []

        async def remove_collaborator(self, repo_full_name: str, username: str):
            self.calls.append(("remove_collaborator", repo_full_name, username))
            return {}

        async def get_repo(self, repo_full_name: str):
            self.calls.append(("get_repo", repo_full_name, ""))
            return {"default_branch": "main"}

        async def get_branch(self, repo_full_name: str, branch: str):
            self.calls.append(("get_branch", repo_full_name, branch))
            return {"commit": {"sha": "cutoff-sha-123"}}

    client = StubGithubClient()
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(enforcement_handler, "get_github_client", lambda: client)

    result = await enforcement_handler.handle_day_close_enforcement(payload)

    assert result["status"] == "cutoff_persisted"
    assert result["candidateSessionId"] == candidate_session.id
    assert result["taskId"] == day2_task.id
    assert result["dayIndex"] == 2
    assert result["cutoffCommitSha"] == "cutoff-sha-123"
    assert result["cutoffAt"] == cutoff_at.isoformat().replace("+00:00", "Z")
    assert result["evalBasisRef"] == "refs/heads/main@cutoff"
    assert result["revokeStatus"] == "collaborator_removed"
    assert client.calls == [
        ("remove_collaborator", "org/candidate-repo", "octocat"),
        ("get_branch", "org/candidate-repo", "main"),
    ]

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is not None
    assert day_audit.cutoff_commit_sha == "cutoff-sha-123"
    observed_cutoff_at = day_audit.cutoff_at
    if observed_cutoff_at.tzinfo is None:
        observed_cutoff_at = observed_cutoff_at.replace(tzinfo=UTC)
    assert observed_cutoff_at == cutoff_at
    assert day_audit.eval_basis_ref == "refs/heads/main@cutoff"


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_is_idempotent_and_no_overwrite(
    async_session,
    monkeypatch,
):
    (
        _simulation,
        candidate_session,
        _day2_task,
        cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)

    class FirstClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def get_repo(self, *_args, **_kwargs):
            return {"default_branch": "main"}

        async def get_branch(self, *_args, **_kwargs):
            return {"commit": {"sha": "first-sha"}}

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: FirstClient(),
    )
    first = await enforcement_handler.handle_day_close_enforcement(payload)
    assert first["status"] == "cutoff_persisted"

    class SecondClient:
        def __init__(self):
            self.calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            self.calls += 1
            return {}

        async def get_repo(self, *_args, **_kwargs):
            self.calls += 1
            return {"default_branch": "main"}

        async def get_branch(self, *_args, **_kwargs):
            self.calls += 1
            return {"commit": {"sha": "second-sha"}}

    second_client = SecondClient()
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: second_client,
    )
    second = await enforcement_handler.handle_day_close_enforcement(payload)
    assert second["status"] == "no_op_cutoff_exists"
    assert second["cutoffCommitSha"] == "first-sha"
    assert second["cutoffAt"] == cutoff_at.isoformat().replace("+00:00", "Z")
    assert second_client.calls == 0

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is not None
    assert day_audit.cutoff_commit_sha == "first-sha"


@pytest.mark.asyncio
async def test_day_close_enforcement_transient_github_failure_is_retried_by_worker(
    async_session,
    monkeypatch,
):
    (
        simulation,
        candidate_session,
        _day2_task,
        _cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)
    now = datetime.now(UTC).replace(microsecond=0)
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        idempotency_key=day_close_enforcement_idempotency_key(candidate_session.id, 2),
        payload_json=payload,
        company_id=simulation.company_id,
        candidate_session_id=candidate_session.id,
        max_attempts=2,
        next_run_at=now,
    )

    class FlakyGithubClient:
        def __init__(self):
            self.remove_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            self.remove_calls += 1
            if self.remove_calls == 1:
                raise GithubError("temporary github failure", status_code=502)
            return {}

        async def get_repo(self, *_args, **_kwargs):
            return {"default_branch": "main"}

        async def get_branch(self, *_args, **_kwargs):
            return {"commit": {"sha": "worker-cutoff-sha"}}

    client = FlakyGithubClient()
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(enforcement_handler, "get_github_client", lambda: client)

    worker.register_handler(
        DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        enforcement_handler.handle_day_close_enforcement,
    )

    first_handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-cutoff-1",
        now=now,
    )
    assert first_handled is True
    first_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert first_refresh is not None
    assert first_refresh.status == JOB_STATUS_QUEUED
    assert first_refresh.attempt == 1

    second_handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-cutoff-2",
        now=now + timedelta(seconds=1),
    )
    assert second_handled is True
    second_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert second_refresh is not None
    assert second_refresh.status == JOB_STATUS_SUCCEEDED
    assert second_refresh.attempt == 2

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is not None
    assert day_audit.cutoff_commit_sha == "worker-cutoff-sha"


@pytest.mark.asyncio
async def test_day_close_enforcement_missing_github_username_retries_and_skips_audit(
    async_session,
    monkeypatch,
):
    (
        simulation,
        candidate_session,
        _day2_task,
        _cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)
    candidate_session.github_username = None
    await async_session.commit()

    now = datetime.now(UTC).replace(microsecond=0)
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        idempotency_key=day_close_enforcement_idempotency_key(candidate_session.id, 2),
        payload_json=payload,
        company_id=simulation.company_id,
        candidate_session_id=candidate_session.id,
        max_attempts=2,
        next_run_at=now,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def get_repo(self, *_args, **_kwargs):
            return {"default_branch": "main"}

        async def get_branch(self, *_args, **_kwargs):
            return {"commit": {"sha": "should-not-be-used"}}

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: StubGithubClient(),
    )
    worker.register_handler(
        DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        enforcement_handler.handle_day_close_enforcement,
    )

    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-missing-identity-1",
        now=now,
    )

    assert handled is True
    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_QUEUED
    assert refreshed.attempt == 1
    assert "day_close_enforcement_missing_github_username" in (
        refreshed.last_error or ""
    )

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is None


def test_day_close_enforcement_parse_helpers():
    assert enforcement_handler._parse_positive_int(True) is None
    assert enforcement_handler._parse_positive_int(0) is None
    assert enforcement_handler._parse_positive_int(-1) is None
    assert enforcement_handler._parse_positive_int(3) == 3
    assert enforcement_handler._parse_positive_int("7") == 7
    assert enforcement_handler._parse_positive_int(" 7 ") is None
    assert enforcement_handler._parse_positive_int("abc") is None

    assert enforcement_handler._parse_optional_datetime(None) is None
    assert enforcement_handler._parse_optional_datetime("   ") is None
    assert enforcement_handler._parse_optional_datetime("not-a-date") is None
    assert enforcement_handler._parse_optional_datetime(
        "2026-03-08T12:00:00"
    ) == datetime(2026, 3, 8, 12, 0, tzinfo=UTC)
    assert enforcement_handler._parse_optional_datetime(
        "2026-03-08T12:00:00+02:00"
    ) == datetime(2026, 3, 8, 10, 0, tzinfo=UTC)

    assert enforcement_handler._to_iso_z(None) is None
    assert (
        enforcement_handler._to_iso_z(datetime(2026, 3, 8, 12, 0))
        == "2026-03-08T12:00:00Z"
    )
    assert (
        enforcement_handler._to_iso_z(datetime(2026, 3, 8, 12, 0, tzinfo=UTC))
        == "2026-03-08T12:00:00Z"
    )

    assert enforcement_handler._extract_head_sha({}) is None
    assert enforcement_handler._extract_head_sha({"commit": {}}) is None
    assert enforcement_handler._extract_head_sha({"commit": {"sha": "  "}}) is None
    assert enforcement_handler._extract_head_sha({"commit": {"sha": " abc "}}) == "abc"


@pytest.mark.asyncio
async def test_day_close_enforcement_resolve_default_branch_variants():
    class Client:
        async def get_repo(self, repo_full_name: str):
            if repo_full_name.endswith("blank"):
                return {"default_branch": "   "}
            return {"default_branch": "develop"}

    client = Client()
    assert (
        await enforcement_handler._resolve_default_branch(
            client,
            repo_full_name="org/repo",
            workspace_default_branch=" feature ",
        )
        == "feature"
    )
    assert (
        await enforcement_handler._resolve_default_branch(
            client,
            repo_full_name="org/repo",
            workspace_default_branch=None,
        )
        == "develop"
    )
    assert (
        await enforcement_handler._resolve_default_branch(
            client,
            repo_full_name="org/repo-blank",
            workspace_default_branch="",
        )
        == "main"
    )


@pytest.mark.asyncio
async def test_day_close_enforcement_revoke_repo_write_access_variants():
    class Client:
        async def remove_collaborator(self, _repo: str, username: str):
            if username == "missing":
                raise GithubError("not found", status_code=404)
            if username == "broken":
                raise GithubError("failure", status_code=500)
            return {}

    client = Client()
    with pytest.raises(
        RuntimeError, match="day_close_enforcement_missing_github_username"
    ):
        await enforcement_handler._revoke_repo_write_access(
            client,
            repo_full_name="org/repo",
            github_username=None,
            candidate_session_id=1,
            day_index=2,
        )
    assert (
        await enforcement_handler._revoke_repo_write_access(
            client,
            repo_full_name="org/repo",
            github_username="missing",
            candidate_session_id=1,
            day_index=2,
        )
        == "collaborator_not_found"
    )
    assert (
        await enforcement_handler._revoke_repo_write_access(
            client,
            repo_full_name="org/repo",
            github_username="octocat",
            candidate_session_id=1,
            day_index=2,
        )
        == "collaborator_removed"
    )
    with pytest.raises(GithubError):
        await enforcement_handler._revoke_repo_write_access(
            client,
            repo_full_name="org/repo",
            github_username="broken",
            candidate_session_id=1,
            day_index=2,
        )


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_invalid_payload():
    result = await enforcement_handler.handle_day_close_enforcement(
        {
            "candidateSessionId": "abc",
            "taskId": 10,
            "dayIndex": 2,
        }
    )
    assert result["status"] == "skipped_invalid_payload"
    assert result["candidateSessionId"] is None


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_candidate_session_not_found(
    async_session,
    monkeypatch,
):
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await enforcement_handler.handle_day_close_enforcement(
        {
            "candidateSessionId": 999999,
            "taskId": 1,
            "dayIndex": 2,
            "windowEndAt": "2026-03-10T21:00:00Z",
        }
    )
    assert result["status"] == "candidate_session_not_found"


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_task_not_found(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(async_session, email="task-missing@test.com")
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
    )
    await async_session.commit()
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await enforcement_handler.handle_day_close_enforcement(
        {
            "candidateSessionId": candidate_session.id,
            "taskId": 999999,
            "dayIndex": 2,
            "windowEndAt": "2026-03-10T21:00:00Z",
        }
    )
    assert result["status"] == "task_not_found"


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_skips_non_code_task(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(async_session, email="non-code-task@test.com")
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    day1_task = next(task for task in tasks if task.day_index == 1)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
    )
    await async_session.commit()
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await enforcement_handler.handle_day_close_enforcement(
        {
            "candidateSessionId": candidate_session.id,
            "taskId": day1_task.id,
            "dayIndex": 2,
            "windowEndAt": "2026-03-10T21:00:00Z",
        }
    )
    assert result["status"] == "skipped_non_code_task"
    assert result["dayIndex"] == 1


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_workspace_missing_raises(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="workspace-missing@test.com"
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    day2_task = next(task for task in tasks if task.day_index == 2)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )

    with pytest.raises(RuntimeError):
        await enforcement_handler.handle_day_close_enforcement(
            {
                "candidateSessionId": candidate_session.id,
                "taskId": day2_task.id,
                "dayIndex": 2,
                "windowEndAt": "2026-03-10T21:00:00Z",
            }
        )


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_missing_branch_sha_raises(
    async_session,
    monkeypatch,
):
    (
        _simulation,
        candidate_session,
        _day2_task,
        _cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)

    class StubGithubClient:
        async def remove_collaborator(self, _repo_full_name: str, _username: str):
            return {}

        async def get_repo(self, _repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, _repo_full_name: str, _branch: str):
            return {"commit": {"sha": "   "}}

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: StubGithubClient(),
    )

    with pytest.raises(RuntimeError):
        await enforcement_handler.handle_day_close_enforcement(payload)

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is None


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_create_once_returns_noop(
    async_session,
    monkeypatch,
):
    (
        _simulation,
        candidate_session,
        day2_task,
        cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)

    class StubGithubClient:
        async def remove_collaborator(self, _repo_full_name: str, _username: str):
            return {}

        async def get_repo(self, _repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, _repo_full_name: str, _branch: str):
            return {"commit": {"sha": "race-sha"}}

    async def _fake_create_day_audit_once(*_args, **_kwargs):
        return (
            SimpleNamespace(
                cutoff_commit_sha="persisted-sha",
                cutoff_at=cutoff_at,
                eval_basis_ref="refs/heads/main@cutoff",
            ),
            False,
        )

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: StubGithubClient(),
    )
    monkeypatch.setattr(
        enforcement_handler.cs_repo,
        "create_day_audit_once",
        _fake_create_day_audit_once,
    )

    result = await enforcement_handler.handle_day_close_enforcement(payload)
    assert result["status"] == "no_op_cutoff_exists"
    assert result["candidateSessionId"] == candidate_session.id
    assert result["taskId"] == day2_task.id
    assert result["dayIndex"] == 2
    assert result["cutoffCommitSha"] == "persisted-sha"
    assert result["evalBasisRef"] == "refs/heads/main@cutoff"


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_collaborator_already_absent_is_idempotent(
    async_session,
    monkeypatch,
):
    (
        _simulation,
        candidate_session,
        _day2_task,
        _cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)

    class StubGithubClient:
        async def remove_collaborator(self, _repo_full_name: str, _username: str):
            raise GithubError("not found", status_code=404)

        async def get_repo(self, _repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, _repo_full_name: str, _branch: str):
            return {"commit": {"sha": "cutoff-sha-idempotent"}}

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: StubGithubClient(),
    )

    result = await enforcement_handler.handle_day_close_enforcement(payload)

    assert result["status"] == "cutoff_persisted"
    assert result["revokeStatus"] == "collaborator_not_found"
    assert result["cutoffCommitSha"] == "cutoff-sha-idempotent"

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is not None
    assert day_audit.cutoff_commit_sha == "cutoff-sha-idempotent"
